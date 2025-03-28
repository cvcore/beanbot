from typing import List, Optional, Dict, Any, Set
import os
import uvicorn
from datetime import date
import logging

from fastapi import Body, FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from beancount.core import data as d

from beanbot.backend.predictor import get_predictor_singleton
from beanbot.common.configs import BeanbotConfig
from beanbot.data.pydantic_serialization import Amount, Transaction
from beanbot.data.container import (
    _BEANBOT_LINENO_RANGE,
    _BEANBOT_UUID,
    TransactionsContainer,
)
from beanbot.helper import logger

# Import custom modules
from beanbot.backend.beanbot_json_encoder import BeanbotJSONResponse
from beanbot.backend.pagination import (
    PaginatedResponse,
    TransactionMetadata,
    TransactionResponse,
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create FastAPI app
app = FastAPI(
    title="Beancount API",
    description="API for Beancount transactions",
    default_response_class=BeanbotJSONResponse,
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
BEANCOUNT_FILE_PATH = os.environ.get("BEANCOUNT_FILE_PATH", "path/to/your/file.bean")
NO_INTERPOLATION = os.environ.get("NO_INTERPOLATION", "true").lower() == "true"

# Global container for transactions
transactions_container = None


@app.on_event("startup")
async def startup_event():
    """Load transactions when the app starts."""
    global transactions_container
    try:
        logger.info(f"Loading Beancount file: {BEANCOUNT_FILE_PATH}")
        transactions_container = TransactionsContainer.load_from_file(
            BEANCOUNT_FILE_PATH, no_interpolation=NO_INTERPOLATION
        )
        BeanbotConfig.get_global().parse_file(BEANCOUNT_FILE_PATH)
        logger.info(f"Loaded {len(transactions_container.entries)} transactions")
    except Exception as e:
        logger.error(f"Error loading Beancount file: {e}", exc_info=True)


def get_container():
    """Dependency to get the transactions container."""
    if transactions_container is None:
        raise HTTPException(status_code=500, detail="Transactions not loaded")
    return transactions_container


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for the API."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return BeanbotJSONResponse(
        status_code=500, content={"detail": "Internal server error"}
    )


def get_collection_metadata(entries: List[Transaction]) -> TransactionMetadata:
    """Extract metadata from a list of transactions."""
    accounts: Set[str] = set()
    payees: Set[str] = set()
    tags: Set[str] = set()
    currencies: Set[str] = set()

    date_range = None
    if entries:
        min_date = min(entry.date for entry in entries)
        max_date = max(entry.date for entry in entries)
        date_range = {"min": min_date, "max": max_date}

        for entry in entries:
            if entry.payee:
                payees.add(entry.payee)
            tags.update(entry.tags)
            for posting in entry.postings:
                accounts.add(posting.account)
                if (
                    isinstance(posting.units, Amount)
                    and posting.units.currency is not None
                ):
                    currencies.add(posting.units.currency)
                if (
                    isinstance(posting.price, Amount)
                    and posting.price.currency is not None
                ):
                    currencies.add(posting.price.currency)

    return TransactionMetadata(
        date_range=date_range,
        account_count=len(accounts),
        payee_count=len(payees),
        tag_count=len(tags),
        currency_count=len(currencies),
    )


@app.get("/api/transactions", response_model=TransactionResponse[Transaction])
async def get_transactions(
    container: TransactionsContainer = Depends(get_container),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    account: Optional[str] = None,
    payee: Optional[str] = None,
    narration: Optional[str] = None,
    tag: Optional[str] = None,
    currency: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Get transactions with pagination and filtering.

    Parameters:
    - from_date: Filter transactions from this date
    - to_date: Filter transactions to this date
    - account: Filter by account name (partial match)
    - payee: Filter by payee (partial match)
    - narration: Filter by narration (partial match)
    - tag: Filter by tag (exact match)
    - currency: Filter by currency (exact match)
    - page: Page number (1-based)
    - page_size: Number of items per page
    """
    try:
        all_entries = container.entries
        filtered_entries = all_entries.copy()

        # Apply filters
        if from_date:
            filtered_entries = [
                entry for entry in filtered_entries if entry.date >= from_date
            ]

        if to_date:
            filtered_entries = [
                entry for entry in filtered_entries if entry.date <= to_date
            ]

        if account:
            account_entries = []
            for entry in filtered_entries:
                for posting in entry.postings:
                    if account.lower() in posting.account.lower():
                        account_entries.append(entry)
                        break
            filtered_entries = account_entries

        if payee:
            filtered_entries = [
                entry
                for entry in filtered_entries
                if entry.payee and payee.lower() in entry.payee.lower()
            ]

        if narration:
            filtered_entries = [
                entry
                for entry in filtered_entries
                if narration.lower() in entry.narration.lower()
            ]

        if tag:
            filtered_entries = [
                entry for entry in filtered_entries if tag in entry.tags
            ]

        if currency:
            currency_entries = []
            for entry in filtered_entries:
                has_currency = False
                for posting in entry.postings:
                    if (
                        isinstance(posting.units, Amount)
                        and posting.units.currency == currency
                        or (
                            isinstance(posting.price, Amount)
                            and posting.price.currency == currency
                        )
                    ):
                        has_currency = True
                        break
                if has_currency:
                    currency_entries.append(entry)
            filtered_entries = currency_entries

        # Sort by date (newest first)
        filtered_entries.sort(key=lambda x: x.date, reverse=True)

        # Calculate pagination
        total_count = len(filtered_entries)
        offset = (page - 1) * page_size
        paginated_entries = filtered_entries[offset : offset + page_size]

        # Create paginated response
        paginated_data = PaginatedResponse.create(
            items=paginated_entries, total=total_count, page=page, size=page_size
        )

        # Get metadata from the filtered entries
        metadata = get_collection_metadata(filtered_entries)

        # Return the response
        return TransactionResponse(data=paginated_data, metadata=metadata)

    except Exception as e:
        logger.error(f"Error retrieving transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving transactions: {str(e)}"
        )


@app.get("/api/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: str, container: TransactionsContainer = Depends(get_container)
):
    """Get a specific transaction by ID."""
    try:
        return container.get_entry_by_id(transaction_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Transaction not found")
    except Exception as e:
        logger.error(
            f"Error retrieving transaction {transaction_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Error retrieving transaction: {str(e)}"
        )


@app.get("/api/accounts")
async def get_accounts(container: TransactionsContainer = Depends(get_container)):
    """Get a list of all accounts used in transactions."""
    try:
        accounts = set()
        for entry in container.entries:
            for posting in entry.postings:
                accounts.add(posting.account)

        # Sort accounts for easier browsing
        return sorted(list(accounts))
    except Exception as e:
        logger.error(f"Error retrieving accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving accounts: {str(e)}"
        )


@app.get("/api/payees")
async def get_payees(container: TransactionsContainer = Depends(get_container)):
    """Get a list of all payees in transactions."""
    try:
        payees = set()
        for entry in container.entries:
            if entry.payee:
                payees.add(entry.payee)

        return sorted(list(payees))
    except Exception as e:
        logger.error(f"Error retrieving payees: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving payees: {str(e)}"
        )


@app.get("/api/tags")
async def get_tags(container: TransactionsContainer = Depends(get_container)):
    """Get a list of all tags used in transactions."""
    try:
        tags = set()
        for entry in container.entries:
            tags.update(entry.tags)

        return sorted(list(tags))
    except Exception as e:
        logger.error(f"Error retrieving tags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving tags: {str(e)}")


@app.get("/api/currencies")
async def get_currencies(container: TransactionsContainer = Depends(get_container)):
    """Get a list of all currencies used in transactions."""
    try:
        currencies = set()
        for entry in container.entries:
            for posting in entry.postings:
                if isinstance(posting.units, Amount):
                    currencies.add(posting.units.currency)
                if isinstance(posting.price, Amount):
                    currencies.add(posting.price.currency)

        currencies.discard(None)
        return sorted(list(currencies))
    except Exception as e:
        logger.error(f"Error retrieving currencies: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving currencies: {str(e)}"
        )


@app.get("/api/info")
async def get_info(container: TransactionsContainer = Depends(get_container)):
    """Get information about the loaded Beancount file."""
    try:
        entries = container.entries
        metadata = get_collection_metadata(entries)

        return {
            "file": BEANCOUNT_FILE_PATH,
            "transaction_count": len(entries),
            "date_range": metadata.date_range,
            "account_count": metadata.account_count,
            "payee_count": metadata.payee_count,
            "tag_count": metadata.tag_count,
            "currency_count": metadata.currency_count,
        }
    except Exception as e:
        logger.error(f"Error retrieving info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving info: {str(e)}")


@app.put("/api/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    transaction_data: Dict[str, Any] = Body(...),
    container: TransactionsContainer = Depends(get_container),
):
    """
    Update a transaction by ID with JSON data.

    Parameters:
    - transaction_id: The UUID of the transaction to update
    - transaction_data: The new transaction data in JSON format

    Returns:
    - The updated transaction
    """
    try:
        # Check if the transaction exists
        try:
            existing_transaction = container.get_entry_by_id(transaction_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Ensure the UUID in the JSON matches the path parameter
        if (
            _BEANBOT_UUID in transaction_data.get("meta", {})
            and transaction_data["meta"][_BEANBOT_UUID] != transaction_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Transaction ID in the URL does not match the ID in the JSON data",
            )

        # Make sure the UUID from the path is preserved in the updated transaction
        if "meta" not in transaction_data:
            transaction_data["meta"] = {}
        transaction_data["meta"][_BEANBOT_UUID] = transaction_id

        # Preserve other important metadata if not provided in the JSON
        if _BEANBOT_LINENO_RANGE not in transaction_data["meta"] and hasattr(
            existing_transaction.meta, _BEANBOT_LINENO_RANGE
        ):
            transaction_data["meta"]["beanbot_lineno_range"] = (
                existing_transaction.meta["beanbot_lineno_range"]
            )

        # Deserialize the JSON to a Transaction object
        try:
            updated_transaction = Transaction.model_validate(transaction_data)
        except Exception as e:
            logger.error(f"Error deserializing transaction data: {e}", exc_info=True)
            raise HTTPException(
                status_code=400, detail=f"Invalid transaction data: {str(e)}"
            )

        # Update the transaction in the container
        container.edit_entry_by_id(transaction_id, updated_transaction)

        # Return the updated transaction
        return updated_transaction

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error updating transaction: {str(e)}"
        )


@app.post("/api/save", status_code=200)
async def save_transactions(container: TransactionsContainer = Depends(get_container)):
    """
    Save all edited transactions to the original Beancount file.

    Returns:
    - Success message
    """
    try:
        # Save the transactions to the file
        container.save()

        return {"message": "Transactions saved successfully"}

    except Exception as e:
        logger.error(f"Error saving transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error saving transactions: {str(e)}"
        )


@app.post("/api/reload", status_code=200)
async def reload_transactions():
    """
    Reload transactions from the Beancount file.

    Returns:
    - Success message
    """
    try:
        global transactions_container

        # Reload transactions from file
        transactions_container = TransactionsContainer.load_from_file(
            BEANCOUNT_FILE_PATH, no_interpolation=NO_INTERPOLATION
        )
        BeanbotConfig.get_global().parse_file(BEANCOUNT_FILE_PATH)

        logger.info(
            f"Reloaded {len(transactions_container.entries)} transactions from file"
        )

        return {
            "message": "Transactions reloaded successfully",
            "count": len(transactions_container.entries),
        }

    except Exception as e:
        logger.error(f"Error reloading transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error reloading transactions: {str(e)}"
        )


@app.post("/api/train", status_code=200)
async def train_classifier(container: TransactionsContainer = Depends(get_container)):
    """
    Train the classifier on the transactions in the container.

    Returns:
    - Success message
    """
    try:
        transactions = container.get_beancount_entries()
        transactions_reviewed = [
            t
            for t in transactions
            if isinstance(t, d.Transaction)
            and not ("_new_dt" in t.tags or "_new_map" in t.tags)
        ]
        predictor = get_predictor_singleton(container.options_map)
        predictor.train(transactions_reviewed)

        if MODEL_PATH := os.environ.get("BEANBOT_MODEL_PATH"):
            logger.info(f"Saving model to {MODEL_PATH}")
            predictor.save_model(MODEL_PATH)

        return {"message": "Classifier trained successfully"}

    except Exception as e:
        logger.error(f"Error training classifier: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error training classifier: {str(e)}"
        )


@app.post("/api/predict", status_code=200)
async def predict_counter_accounts(
    transaction_ids: List[str] = Body(...),
    container: TransactionsContainer = Depends(get_container),
):
    """
    Predict counter accounts for given transaction IDs.

    Parameters:
    - transaction_ids: List of transaction IDs to predict counter accounts for

    Returns:
    - Dictionary mapping transaction IDs to their predicted counter accounts
    """
    try:
        # Get the transactions from the container
        transactions = []
        for tx_id in transaction_ids:
            try:
                tx = container.get_entry_by_id(tx_id)
                transactions.append(tx.to_beancount())
            except KeyError:
                raise HTTPException(
                    status_code=404, detail=f"Transaction with ID {tx_id} not found"
                )

        # Get the predictor singleton and make predictions
        predictor = get_predictor_singleton(container.options_map)
        accounts, scores = zip(*predictor.predict_accounts(transactions))
        accounts = list(accounts)
        scores = [float(score) for score in scores]

        return {
            "message": "Predictions completed successfully",
            "predictions": list(accounts),
            "scores": scores,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error predicting counter accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error predicting counter accounts: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "beanbot.backend.beanbot_api:app", host="0.0.0.0", port=8000, reload=True
    )
