from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi_websocket_pubsub import PubSubClient, PubSubEndpoint, Topic
from redis.asyncio import Redis

from app.core.auth import get_current_user
from app.db.models.user import User
from app.db.redis import get_redis_dep

router = APIRouter()

# Initialize the pubsub endpoint
# In a real app, you might want to use a Redis broker for scalability
# For simplicity, we'll use an in-memory broker first.
# If Redis broker is desired, it would be:
# from fastapi_websocket_pubsub.pub_sub_client import RedisBroker
# broker = RedisBroker(redis_url="redis://localhost:6379/0") # or your settings.redis_url
# endpoint = PubSubEndpoint(broker=broker)

# For now, using in-memory broker:
endpoint = PubSubEndpoint()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: Annotated[User, Depends(get_current_user)], # Authenticate user
    redis: Annotated[Redis, Depends(get_redis_dep)], # Can be used for Redis broker or other state
):
    """
    WebSocket endpoint for students to connect and receive real-time updates.
    Each student subscribes to their user_id channel.
    """
    user_id_str = str(user.id)
    # The client will automatically subscribe to topics it receives from the server on connect
    # Here, we directly subscribe the connection to the user's private channel
    await endpoint.main_logic(websocket, [Topic(user_id_str)])
