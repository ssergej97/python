import asyncio
import random
import uuid

import httpx
from fastapi import FastAPI, BackgroundTasks
from typing import Literal
from pydantic import BaseModel

OrderStatus = Literal["not started", "cooking", "cooked", "finished"]

STORAGE: dict[str, OrderStatus] = {}

CATERING_API_WEBHOOK_URL = "http://localhost:8000/webhooks/kfc"
app = FastAPI()


class OrderItem(BaseModel):
    dish: str
    quantity: int


class OrderRequestBody(BaseModel):
    order: list[OrderItem]


async def update_order_status(order_id: str):
    ORDER_STATUSES: tuple[OrderStatus, ...] = ("cooking", "cooked", "finished")
    for status in ORDER_STATUSES:
        await asyncio.sleep(random.randint(1, 2))
        STORAGE[order_id] = status

        async with httpx.AsyncClient() as client:
            await client.post(
                CATERING_API_WEBHOOK_URL, data={"id": order_id, "status": status}
            )



@app.post("/api/orders")
async def make_order(body: OrderRequestBody, background_tasks: BackgroundTasks):
    print(body)

    order_id = str(uuid.uuid4())
    STORAGE[order_id] = "not started"
    background_tasks.add_task(update_order_status, order_id)

    return {
        "id": order_id,
        "status": "not started"
    }


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    return STORAGE.get(order_id, {"error": "No such order"})