"""
FastAPI backend for Alex Financial Advisor
Handles all API routes with Clerk JWT authentication
Supports versioned API endpoints (/api/v1/) with OpenAPI documentation
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid

from fastapi import FastAPI, HTTPException, Depends, status, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
import boto3
from mangum import Mangum
from dotenv import load_dotenv
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials

from src import Database
from src.schemas import (
    UserCreate,
    AccountCreate,
    PositionCreate,
    JobCreate, JobUpdate,
    JobType, JobStatus
)

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API version
API_VERSION = "1.0.0"

# Initialize FastAPI app with OpenAPI metadata
app = FastAPI(
    title="Alex Financial Advisor API",
    description=(
        "Backend API for AI-powered financial planning.\n\n"
        "## Versioning\n"
        "All endpoints are versioned under `/api/v1/`. "
        "Legacy unversioned `/api/` endpoints are deprecated and will be removed in a future release.\n\n"
        "## Authentication\n"
        "All endpoints (except `/health`) require a valid Clerk JWT token "
        "in the `Authorization: Bearer <token>` header."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration
# Get origins from CORS_ORIGINS env var (comma-separated) or fall back to localhost
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers for better error messages
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with user-friendly messages"""
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid input data. Please check your request and try again."}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with improved messages"""
    # Map technical errors to user-friendly messages
    user_friendly_messages = {
        401: "Your session has expired. Please sign in again.",
        403: "You don't have permission to access this resource.",
        404: "The requested resource was not found.",
        429: "Too many requests. Please slow down and try again later.",
        500: "An internal error occurred. Please try again later.",
        503: "The service is temporarily unavailable. Please try again later."
    }

    message = user_friendly_messages.get(exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": message}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Our team has been notified."}
    )

# Initialize services
db = Database()

# SQS client for job queueing
sqs_client = boto3.client('sqs', region_name=os.getenv('DEFAULT_AWS_REGION', 'us-east-1'))
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL', '')

# Clerk authentication setup (exactly like saas reference)
clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)

async def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(clerk_guard)) -> str:
    """Extract user ID from validated Clerk token"""
    # The clerk_guard dependency already validated the token
    # creds.decoded contains the JWT payload
    user_id = creds.decoded["sub"]
    logger.info(f"Authenticated user: {user_id}")
    return user_id

# ─── Response Models (for OpenAPI documentation) ────────────────────────────

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status", examples=["healthy"])
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    api_version: str = Field(..., description="Current API version")

class UserDetail(BaseModel):
    """User profile details"""
    clerk_user_id: str = Field(..., description="Clerk authentication user ID")
    display_name: str = Field(..., description="User display name")
    years_until_retirement: int = Field(..., description="Years until planned retirement")
    target_retirement_income: float = Field(..., description="Annual target retirement income in USD")
    asset_class_targets: Dict[str, float] = Field(..., description="Target asset class allocation percentages")
    region_targets: Dict[str, float] = Field(..., description="Target region allocation percentages")

    class Config:
        extra = "allow"

class UserResponse(BaseModel):
    """Response for user get/create"""
    user: Dict[str, Any] = Field(..., description="User profile data")
    created: bool = Field(..., description="Whether the user was newly created")

class UserUpdate(BaseModel):
    """Update user settings"""
    display_name: Optional[str] = None
    years_until_retirement: Optional[int] = None
    target_retirement_income: Optional[float] = None
    asset_class_targets: Optional[Dict[str, float]] = None
    region_targets: Optional[Dict[str, float]] = None

class AccountResponse(BaseModel):
    """Account details"""
    id: str
    clerk_user_id: str
    account_name: str
    account_purpose: Optional[str] = None
    cash_balance: float = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        extra = "allow"

class AccountUpdate(BaseModel):
    """Update account"""
    account_name: Optional[str] = None
    account_purpose: Optional[str] = None
    cash_balance: Optional[float] = None

class InstrumentResponse(BaseModel):
    """Instrument summary for autocomplete"""
    symbol: str
    name: str
    instrument_type: str
    current_price: Optional[float] = None

class PositionResponse(BaseModel):
    """Position details"""
    id: str
    account_id: str
    symbol: str
    quantity: float
    instrument: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        extra = "allow"

class PositionListResponse(BaseModel):
    """List of positions for an account"""
    positions: List[Dict[str, Any]]

class PositionUpdate(BaseModel):
    """Update position"""
    quantity: Optional[float] = None

class AnalyzeRequest(BaseModel):
    """Request to trigger portfolio analysis"""
    analysis_type: str = Field(default="portfolio", description="Type of analysis to perform")
    options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")

class AnalyzeResponse(BaseModel):
    """Response after triggering analysis"""
    job_id: str = Field(..., description="Unique job identifier")
    message: str = Field(..., description="Status message")

class JobResponse(BaseModel):
    """Analysis job status and results"""
    id: str
    clerk_user_id: str
    job_type: str
    status: str = Field(..., description="Job status: pending, running, completed, failed")
    request_payload: Optional[Dict[str, Any]] = None
    report_payload: Optional[Dict[str, Any]] = None
    charts_payload: Optional[Dict[str, Any]] = None
    retirement_payload: Optional[Dict[str, Any]] = None
    summary_payload: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        extra = "allow"

class JobListResponse(BaseModel):
    """List of analysis jobs"""
    jobs: List[Dict[str, Any]]

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str

class ResetAccountsResponse(BaseModel):
    """Response for account reset"""
    message: str
    accounts_deleted: int

class PopulateTestDataResponse(BaseModel):
    """Response for test data population"""
    message: str
    accounts_created: int
    accounts: List[Dict[str, Any]]

class ErrorResponse(BaseModel):
    """Error response"""
    detail: str = Field(..., description="Error description")

# ─── Versioned API Router (v1) ──────────────────────────────────────────────

v1_router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)

# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Health check endpoint (no authentication required)"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_version": API_VERSION,
    }

# ─── User Endpoints ─────────────────────────────────────────────────────────

@v1_router.get("/user", response_model=UserResponse, tags=["users"],
               summary="Get or create user",
               responses={404: {"model": ErrorResponse}})
async def get_or_create_user(
    clerk_user_id: str = Depends(get_current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard)
):
    """Get the current user's profile, or create one with defaults on first login."""

    try:
        # Check if user exists
        user = db.users.find_by_clerk_id(clerk_user_id)

        if user:
            return UserResponse(user=user, created=False)

        # Create new user with defaults from JWT token
        token_data = creds.decoded
        display_name = token_data.get('name') or token_data.get('email', '').split('@')[0] or "New User"

        # Create user with ALL defaults in one operation
        user_data = {
            'clerk_user_id': clerk_user_id,
            'display_name': display_name,
            'years_until_retirement': 20,
            'target_retirement_income': 60000,
            'asset_class_targets': {"equity": 70, "fixed_income": 30},
            'region_targets': {"north_america": 50, "international": 50}
        }

        # Insert directly with all data
        created_clerk_id = db.users.db.insert('users', user_data, returning='clerk_user_id')

        # Fetch the created user
        created_user = db.users.find_by_clerk_id(clerk_user_id)
        logger.info(f"Created new user: {clerk_user_id}")

        return UserResponse(user=created_user, created=True)

    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        raise HTTPException(status_code=500, detail="Failed to load user profile")

@v1_router.put("/user", tags=["users"],
               summary="Update user settings")
async def update_user(user_update: UserUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """Update the current user's profile settings (retirement goals, targets, etc.)."""

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user - users table uses clerk_user_id as primary key
        update_data = user_update.model_dump(exclude_unset=True)

        # Use the database client directly since users table has clerk_user_id as PK
        db.users.db.update(
            'users',
            update_data,
            "clerk_user_id = :clerk_user_id",
            {'clerk_user_id': clerk_user_id}
        )

        # Return updated user
        updated_user = db.users.find_by_clerk_id(clerk_user_id)
        return updated_user

    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Account Endpoints ──────────────────────────────────────────────────────

@v1_router.get("/accounts", tags=["accounts"],
               summary="List accounts")
async def list_accounts(clerk_user_id: str = Depends(get_current_user_id)):
    """List all investment accounts for the current user."""

    try:
        # Get accounts for user
        accounts = db.accounts.find_by_user(clerk_user_id)
        return accounts

    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/accounts", tags=["accounts"],
                summary="Create account",
                status_code=status.HTTP_201_CREATED)
async def create_account(account: AccountCreate, clerk_user_id: str = Depends(get_current_user_id)):
    """Create a new investment account."""

    try:
        # Verify user exists
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create account
        account_id = db.accounts.create_account(
            clerk_user_id=clerk_user_id,
            account_name=account.account_name,
            account_purpose=account.account_purpose,
            cash_balance=getattr(account, 'cash_balance', Decimal('0'))
        )

        # Return created account
        created_account = db.accounts.find_by_id(account_id)
        return created_account

    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.put("/accounts/{account_id}", tags=["accounts"],
               summary="Update account",
               responses={404: {"model": ErrorResponse}})
async def update_account(account_id: str, account_update: AccountUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """Update an existing account's name, purpose, or cash balance."""

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Verify ownership - accounts table stores clerk_user_id directly
        if account.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Update account
        update_data = account_update.model_dump(exclude_unset=True)
        db.accounts.update(account_id, update_data)

        # Return updated account
        updated_account = db.accounts.find_by_id(account_id)
        return updated_account

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.delete("/accounts/{account_id}", response_model=MessageResponse, tags=["accounts"],
                  summary="Delete account",
                  responses={404: {"model": ErrorResponse}})
async def delete_account(account_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Delete an account and all its positions (cascade delete)."""

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Verify ownership - accounts table stores clerk_user_id directly
        if account.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Delete all positions first (due to foreign key constraint)
        positions = db.positions.find_by_account(account_id)
        for position in positions:
            db.positions.delete(position['id'])

        # Delete the account
        db.accounts.delete(account_id)

        return {"message": "Account deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.get("/accounts/{account_id}/positions", response_model=PositionListResponse,
               tags=["accounts"],
               summary="List positions for account",
               responses={404: {"model": ErrorResponse}})
async def list_positions(account_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get all positions for a specific account, including instrument details."""

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Verify ownership - accounts table stores clerk_user_id directly
        if account.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        positions = db.positions.find_by_account(account_id)

        # Format positions with instrument data for frontend
        formatted_positions = []
        for pos in positions:
            # Get full instrument data
            instrument = db.instruments.find_by_symbol(pos['symbol'])
            formatted_positions.append({
                **pos,
                'instrument': instrument
            })

        return {"positions": formatted_positions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Position Endpoints ─────────────────────────────────────────────────────

@v1_router.post("/positions", tags=["positions"],
                summary="Create position",
                status_code=status.HTTP_201_CREATED)
async def create_position(position: PositionCreate, clerk_user_id: str = Depends(get_current_user_id)):
    """Add a position to an account. Auto-creates the instrument if it doesn't exist."""

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(position.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Verify ownership - accounts table stores clerk_user_id directly
        if account.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Check if instrument exists, if not create it
        instrument = db.instruments.find_by_symbol(position.symbol.upper())
        if not instrument:
            logger.info(f"Creating new instrument: {position.symbol.upper()}")
            # Create a basic instrument entry with default allocations
            # Import the schema from database
            from src.schemas import InstrumentCreate

            # Determine type based on common patterns
            symbol_upper = position.symbol.upper()
            if len(symbol_upper) <= 5 and symbol_upper.isalpha():
                instrument_type = "stock"
            else:
                instrument_type = "etf"

            # Create instrument with basic default allocations
            # These can be updated later by the tagger agent
            new_instrument = InstrumentCreate(
                symbol=symbol_upper,
                name=f"{symbol_upper} - User Added",  # Basic name, can be updated later
                instrument_type=instrument_type,
                current_price=Decimal("0.00"),  # Price will be updated by background processes
                allocation_regions={"north_america": 100.0},  # Default to 100% NA
                allocation_sectors={"other": 100.0},  # Default to 100% other
                allocation_asset_class={"equity": 100.0} if instrument_type == "stock" else {"fixed_income": 100.0}
            )

            db.instruments.create_instrument(new_instrument)

        # Add position
        position_id = db.positions.add_position(
            account_id=position.account_id,
            symbol=position.symbol.upper(),
            quantity=position.quantity
        )

        # Return created position
        created_position = db.positions.find_by_id(position_id)
        return created_position

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.put("/positions/{position_id}", tags=["positions"],
               summary="Update position",
               responses={404: {"model": ErrorResponse}})
async def update_position(position_id: str, position_update: PositionUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """Update an existing position's quantity."""

    try:
        # Get position and verify ownership
        position = db.positions.find_by_id(position_id)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        account = db.accounts.find_by_id(position['account_id'])
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Verify ownership - accounts table stores clerk_user_id directly
        if account.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Update position
        update_data = position_update.model_dump(exclude_unset=True)
        db.positions.update(position_id, update_data)

        # Return updated position
        updated_position = db.positions.find_by_id(position_id)
        return updated_position

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.delete("/positions/{position_id}", response_model=MessageResponse,
                  tags=["positions"],
                  summary="Delete position",
                  responses={404: {"model": ErrorResponse}})
async def delete_position(position_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Delete a position from an account."""

    try:
        # Get position and verify ownership
        position = db.positions.find_by_id(position_id)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        account = db.accounts.find_by_id(position['account_id'])
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Verify ownership - accounts table stores clerk_user_id directly
        if account.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        db.positions.delete(position_id)
        return {"message": "Position deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Instrument Endpoints ───────────────────────────────────────────────────

@v1_router.get("/instruments", response_model=List[InstrumentResponse],
               tags=["instruments"],
               summary="List instruments")
async def list_instruments(clerk_user_id: str = Depends(get_current_user_id)):
    """Get all available instruments for autocomplete/search."""

    try:
        instruments = db.instruments.find_all()
        # Return simplified list for autocomplete
        return [
            {
                "symbol": inst["symbol"],
                "name": inst["name"],
                "instrument_type": inst["instrument_type"],
                "current_price": float(inst["current_price"]) if inst.get("current_price") else None
            }
            for inst in instruments
        ]
    except Exception as e:
        logger.error(f"Error fetching instruments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Analysis Endpoints ─────────────────────────────────────────────────────

@v1_router.post("/analyze", response_model=AnalyzeResponse,
                tags=["analysis"],
                summary="Trigger portfolio analysis",
                status_code=status.HTTP_202_ACCEPTED)
async def trigger_analysis(request: AnalyzeRequest, clerk_user_id: str = Depends(get_current_user_id)):
    """Trigger an AI-powered portfolio analysis. Creates a job and queues it for processing."""

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create job
        job_id = db.jobs.create_job(
            clerk_user_id=clerk_user_id,
            job_type="portfolio_analysis",
            request_payload=request.model_dump()
        )

        # Get the created job
        job = db.jobs.find_by_id(job_id)

        # Send to SQS
        if SQS_QUEUE_URL:
            message = {
                'job_id': str(job_id),
                'clerk_user_id': clerk_user_id,
                'analysis_type': request.analysis_type,
                'options': request.options
            }

            sqs_client.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            logger.info(f"Sent analysis job to SQS: {job_id}")
        else:
            logger.warning("SQS_QUEUE_URL not configured, job created but not queued")

        return AnalyzeResponse(
            job_id=str(job_id),
            message="Analysis started. Check job status for results."
        )

    except Exception as e:
        logger.error(f"Error triggering analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Job Endpoints ───────────────────────────────────────────────────────────

@v1_router.get("/jobs/{job_id}", tags=["jobs"],
               summary="Get job status",
               responses={404: {"model": ErrorResponse}})
async def get_job_status(job_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get the status and results of an analysis job."""

    try:
        # Get job
        job = db.jobs.find_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify job belongs to user - jobs table stores clerk_user_id directly
        if job.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.get("/jobs", response_model=JobListResponse,
               tags=["jobs"],
               summary="List jobs")
async def list_jobs(clerk_user_id: str = Depends(get_current_user_id)):
    """List all analysis jobs for the current user, ordered by most recent first."""

    try:
        # Get jobs for this user (with higher limit to avoid missing recent jobs)
        user_jobs = db.jobs.find_by_user(clerk_user_id, limit=100)
        # Sort by created_at descending (most recent first)
        user_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return {"jobs": user_jobs}

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Admin Endpoints ────────────────────────────────────────────────────────

@v1_router.delete("/reset-accounts", response_model=ResetAccountsResponse,
                  tags=["admin"],
                  summary="Reset all accounts")
async def reset_accounts(clerk_user_id: str = Depends(get_current_user_id)):
    """Delete all accounts and positions for the current user."""

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get all accounts for user
        accounts = db.accounts.find_by_user(clerk_user_id)

        # Delete each account (positions will cascade delete)
        deleted_count = 0
        for account in accounts:
            try:
                # Positions are deleted automatically via CASCADE
                db.accounts.delete(account['id'])
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Could not delete account {account['id']}: {e}")

        return {
            "message": f"Deleted {deleted_count} account(s)",
            "accounts_deleted": deleted_count
        }

    except Exception as e:
        logger.error(f"Error resetting accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/populate-test-data", response_model=PopulateTestDataResponse,
                tags=["admin"],
                summary="Populate test data")
async def populate_test_data(clerk_user_id: str = Depends(get_current_user_id)):
    """Populate sample portfolio data for testing (3 accounts with positions)."""

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Define missing instruments that might not be in the database
        missing_instruments = {
            "AAPL": {
                "name": "Apple Inc.",
                "type": "stock",
                "current_price": 195.89,
                "allocation_regions": {"north_america": 100},
                "allocation_sectors": {"technology": 100},
                "allocation_asset_class": {"equity": 100}
            },
            "AMZN": {
                "name": "Amazon.com Inc.",
                "type": "stock",
                "current_price": 178.35,
                "allocation_regions": {"north_america": 100},
                "allocation_sectors": {"consumer_discretionary": 100},
                "allocation_asset_class": {"equity": 100}
            },
            "NVDA": {
                "name": "NVIDIA Corporation",
                "type": "stock",
                "current_price": 522.74,
                "allocation_regions": {"north_america": 100},
                "allocation_sectors": {"technology": 100},
                "allocation_asset_class": {"equity": 100}
            },
            "MSFT": {
                "name": "Microsoft Corporation",
                "type": "stock",
                "current_price": 430.82,
                "allocation_regions": {"north_america": 100},
                "allocation_sectors": {"technology": 100},
                "allocation_asset_class": {"equity": 100}
            },
            "GOOGL": {
                "name": "Alphabet Inc. Class A",
                "type": "stock",
                "current_price": 173.69,
                "allocation_regions": {"north_america": 100},
                "allocation_sectors": {"technology": 100},
                "allocation_asset_class": {"equity": 100}
            },
        }

        # Check and add missing instruments
        for symbol, info in missing_instruments.items():
            existing = db.instruments.find_by_symbol(symbol)
            if not existing:
                try:
                    from src.schemas import InstrumentCreate

                    instrument_data = InstrumentCreate(
                        symbol=symbol,
                        name=info["name"],
                        instrument_type=info["type"],
                        current_price=Decimal(str(info["current_price"])),
                        allocation_regions=info["allocation_regions"],
                        allocation_sectors=info["allocation_sectors"],
                        allocation_asset_class=info["allocation_asset_class"]
                    )
                    db.instruments.create_instrument(instrument_data)
                    logger.info(f"Added missing instrument: {symbol}")
                except Exception as e:
                    logger.warning(f"Could not add instrument {symbol}: {e}")

        # Create accounts with test data
        accounts_data = [
            {
                "name": "401k Long-term",
                "purpose": "Primary retirement savings account with employer match",
                "cash": 5000.00,
                "positions": [
                    ("SPY", 150),   # S&P 500 ETF
                    ("VTI", 100),   # Total Stock Market ETF
                    ("BND", 200),   # Bond ETF
                    ("QQQ", 75),    # Nasdaq ETF
                    ("IWM", 50),    # Small Cap ETF
                ]
            },
            {
                "name": "Roth IRA",
                "purpose": "Tax-free retirement growth account",
                "cash": 2500.00,
                "positions": [
                    ("VTI", 80),    # Total Stock Market ETF
                    ("VXUS", 60),   # International Stock ETF
                    ("VNQ", 40),    # Real Estate ETF
                    ("GLD", 25),    # Gold ETF
                    ("TLT", 30),    # Long-term Treasury ETF
                    ("VIG", 45),    # Dividend Growth ETF
                ]
            },
            {
                "name": "Brokerage Account",
                "purpose": "Taxable investment account for individual stocks",
                "cash": 10000.00,
                "positions": [
                    ("TSLA", 15),   # Tesla
                    ("AAPL", 50),   # Apple
                    ("AMZN", 10),   # Amazon
                    ("NVDA", 25),   # Nvidia
                    ("MSFT", 30),   # Microsoft
                    ("GOOGL", 20),  # Google
                ]
            }
        ]

        created_accounts = []
        for account_data in accounts_data:
            # Create account
            account_id = db.accounts.create_account(
                clerk_user_id=clerk_user_id,
                account_name=account_data["name"],
                account_purpose=account_data["purpose"],
                cash_balance=Decimal(str(account_data["cash"]))
            )

            # Add positions
            for symbol, quantity in account_data["positions"]:
                try:
                    db.positions.add_position(
                        account_id=account_id,
                        symbol=symbol,
                        quantity=Decimal(str(quantity))
                    )
                except Exception as e:
                    logger.warning(f"Could not add position {symbol}: {e}")

            created_accounts.append(account_id)

        # Get all accounts with their positions for summary
        all_accounts = []
        for account_id in created_accounts:
            account = db.accounts.find_by_id(account_id)
            positions = db.positions.find_by_account(account_id)
            account['positions'] = positions
            all_accounts.append(account)

        return {
            "message": "Test data populated successfully",
            "accounts_created": len(created_accounts),
            "accounts": all_accounts
        }

    except Exception as e:
        logger.error(f"Error populating test data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Register v1 router ─────────────────────────────────────────────────────

app.include_router(v1_router)

# ─── Deprecated /api/ routes (backward compatibility) ────────────────────────
# These routes forward to the v1 implementations but add a Deprecation header.
# They will be removed in a future API version.

deprecated_router = APIRouter(
    prefix="/api",
    tags=["deprecated"],
    deprecated=True,
)

DEPRECATION_NOTICE = "This endpoint is deprecated. Use /api/v1/ prefix instead."


def _deprecated_response(result):
    """Wrap a result in a JSONResponse with deprecation headers."""
    if isinstance(result, JSONResponse):
        result.headers["Deprecation"] = "true"
        result.headers["Sunset"] = "2026-09-01"
        result.headers["Link"] = '</api/v1/>; rel="successor-version"'
        return result
    # For dict/list results, wrap in JSONResponse
    response = JSONResponse(content=result)
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-09-01"
    response.headers["Link"] = '</api/v1/>; rel="successor-version"'
    return response


@deprecated_router.get("/user", response_model=UserResponse, tags=["deprecated"],
                       summary="[Deprecated] Get or create user")
async def deprecated_get_or_create_user(
    clerk_user_id: str = Depends(get_current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard)
):
    """**Deprecated**: Use `GET /api/v1/user` instead."""
    logger.warning(f"Deprecated endpoint called: GET /api/user by {clerk_user_id}")
    return await get_or_create_user(clerk_user_id, creds)

@deprecated_router.put("/user", tags=["deprecated"],
                       summary="[Deprecated] Update user")
async def deprecated_update_user(user_update: UserUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `PUT /api/v1/user` instead."""
    logger.warning(f"Deprecated endpoint called: PUT /api/user by {clerk_user_id}")
    return await update_user(user_update, clerk_user_id)

@deprecated_router.get("/accounts", tags=["deprecated"],
                       summary="[Deprecated] List accounts")
async def deprecated_list_accounts(clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `GET /api/v1/accounts` instead."""
    logger.warning(f"Deprecated endpoint called: GET /api/accounts by {clerk_user_id}")
    return await list_accounts(clerk_user_id)

@deprecated_router.post("/accounts", tags=["deprecated"],
                        summary="[Deprecated] Create account")
async def deprecated_create_account(account: AccountCreate, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `POST /api/v1/accounts` instead."""
    logger.warning(f"Deprecated endpoint called: POST /api/accounts by {clerk_user_id}")
    return await create_account(account, clerk_user_id)

@deprecated_router.put("/accounts/{account_id}", tags=["deprecated"],
                       summary="[Deprecated] Update account")
async def deprecated_update_account(account_id: str, account_update: AccountUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `PUT /api/v1/accounts/{id}` instead."""
    logger.warning(f"Deprecated endpoint called: PUT /api/accounts/{account_id} by {clerk_user_id}")
    return await update_account(account_id, account_update, clerk_user_id)

@deprecated_router.delete("/accounts/{account_id}", tags=["deprecated"],
                          summary="[Deprecated] Delete account")
async def deprecated_delete_account(account_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `DELETE /api/v1/accounts/{id}` instead."""
    logger.warning(f"Deprecated endpoint called: DELETE /api/accounts/{account_id} by {clerk_user_id}")
    return await delete_account(account_id, clerk_user_id)

@deprecated_router.get("/accounts/{account_id}/positions", tags=["deprecated"],
                       summary="[Deprecated] List positions")
async def deprecated_list_positions(account_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `GET /api/v1/accounts/{id}/positions` instead."""
    logger.warning(f"Deprecated endpoint called: GET /api/accounts/{account_id}/positions by {clerk_user_id}")
    return await list_positions(account_id, clerk_user_id)

@deprecated_router.post("/positions", tags=["deprecated"],
                        summary="[Deprecated] Create position")
async def deprecated_create_position(position: PositionCreate, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `POST /api/v1/positions` instead."""
    logger.warning(f"Deprecated endpoint called: POST /api/positions by {clerk_user_id}")
    return await create_position(position, clerk_user_id)

@deprecated_router.put("/positions/{position_id}", tags=["deprecated"],
                       summary="[Deprecated] Update position")
async def deprecated_update_position(position_id: str, position_update: PositionUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `PUT /api/v1/positions/{id}` instead."""
    logger.warning(f"Deprecated endpoint called: PUT /api/positions/{position_id} by {clerk_user_id}")
    return await update_position(position_id, position_update, clerk_user_id)

@deprecated_router.delete("/positions/{position_id}", tags=["deprecated"],
                          summary="[Deprecated] Delete position")
async def deprecated_delete_position(position_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `DELETE /api/v1/positions/{id}` instead."""
    logger.warning(f"Deprecated endpoint called: DELETE /api/positions/{position_id} by {clerk_user_id}")
    return await delete_position(position_id, clerk_user_id)

@deprecated_router.get("/instruments", tags=["deprecated"],
                       summary="[Deprecated] List instruments")
async def deprecated_list_instruments(clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `GET /api/v1/instruments` instead."""
    logger.warning(f"Deprecated endpoint called: GET /api/instruments by {clerk_user_id}")
    return await list_instruments(clerk_user_id)

@deprecated_router.post("/analyze", tags=["deprecated"],
                        summary="[Deprecated] Trigger analysis")
async def deprecated_trigger_analysis(request: AnalyzeRequest, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `POST /api/v1/analyze` instead."""
    logger.warning(f"Deprecated endpoint called: POST /api/analyze by {clerk_user_id}")
    return await trigger_analysis(request, clerk_user_id)

@deprecated_router.get("/jobs/{job_id}", tags=["deprecated"],
                       summary="[Deprecated] Get job status")
async def deprecated_get_job_status(job_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `GET /api/v1/jobs/{id}` instead."""
    logger.warning(f"Deprecated endpoint called: GET /api/jobs/{job_id} by {clerk_user_id}")
    return await get_job_status(job_id, clerk_user_id)

@deprecated_router.get("/jobs", tags=["deprecated"],
                       summary="[Deprecated] List jobs")
async def deprecated_list_jobs(clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `GET /api/v1/jobs` instead."""
    logger.warning(f"Deprecated endpoint called: GET /api/jobs by {clerk_user_id}")
    return await list_jobs(clerk_user_id)

@deprecated_router.delete("/reset-accounts", tags=["deprecated"],
                          summary="[Deprecated] Reset accounts")
async def deprecated_reset_accounts(clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `DELETE /api/v1/reset-accounts` instead."""
    logger.warning(f"Deprecated endpoint called: DELETE /api/reset-accounts by {clerk_user_id}")
    return await reset_accounts(clerk_user_id)

@deprecated_router.post("/populate-test-data", tags=["deprecated"],
                        summary="[Deprecated] Populate test data")
async def deprecated_populate_test_data(clerk_user_id: str = Depends(get_current_user_id)):
    """**Deprecated**: Use `POST /api/v1/populate-test-data` instead."""
    logger.warning(f"Deprecated endpoint called: POST /api/populate-test-data by {clerk_user_id}")
    return await populate_test_data(clerk_user_id)

app.include_router(deprecated_router)

# Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
