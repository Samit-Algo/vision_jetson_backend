"""
FastAPI Application
===================

Main FastAPI app setup with all routes and middleware.
Starts: Runner → CameraPublisher → Streaming Service
"""
import asyncio
import threading
from pathlib import Path
from multiprocessing import Manager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.v1 import camera_router, agent_router, device_router
from app.processing.runner.runner import main as run_runner
from app.application.services.streaming_service import StreamingService


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    This function sets up the FastAPI application with:
    - Environment variable loading
    - CORS middleware configuration
    - API route registration
    - Startup/shutdown event handlers for Runner and Streaming Service
    
    Returns:
        Configured FastAPI application instance
    """
    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
    
    # Create FastAPI app
    application = FastAPI(
        title="Agent Camera API",
        description="Production-ready API for camera management and WebRTC configuration",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure allowed origins for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register API routers
    application.include_router(camera_router, prefix="/api/v1/cameras")
    application.include_router(agent_router, prefix="/api/v1/agents")
    application.include_router(device_router, prefix="/api/v1/devices")
    
    # Global shared store (shared between Runner and Streaming Service)
    _shared_store = None
    _streaming_service = None


    def get_shared_store():
        """Get or create shared store (singleton)."""
        nonlocal _shared_store
        if _shared_store is None:
            manager = Manager()
            _shared_store = manager.dict()
        return _shared_store


    async def monitor_cameras_and_start_streams():
        """
        Periodically check for active cameras and agents, start/stop AWS streams.
        """
        from app.infrastructure.db.mongo_camera_repository import MongoCameraRepository
        from app.infrastructure.db.mongo_agent_repository import MongoAgentRepository
        
        # MongoCameraRepository auto-initializes MongoDB client internally
        camera_repo = MongoCameraRepository()
        agent_repo = MongoAgentRepository()
        
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                if not _streaming_service or not _streaming_service.is_running():
                    continue
                
                # ============================================================
                # Monitor Camera Streams (Raw Video)
                # ============================================================
                active_cameras = camera_repo.find_all_active()
                active_camera_keys = {f"{cam.owner_user_id}:{cam.id}" for cam in active_cameras}
                
                # Start streams for new cameras
                for camera in active_cameras:
                    key = f"{camera.owner_user_id}:{camera.id}"
                    if key not in _streaming_service._clients:
                        await _streaming_service.start_camera_stream(camera.owner_user_id, camera.id)
                
                # Stop streams for inactive cameras
                for key in list(_streaming_service._clients.keys()):
                    if key not in active_camera_keys:
                        user_id, camera_id = key.split(":", 1)
                        await _streaming_service.stop_camera_stream(user_id, camera_id)
                
                # ============================================================
                # Monitor Agent Streams (Processed Video with Bounding Boxes)
                # ============================================================
                active_agents = agent_repo.find_all_active()
                
                # Get owner_user_id for each agent from camera
                active_agent_keys = set()
                for agent in active_agents:
                    camera = camera_repo.find_by_id(agent.camera_id)
                    if camera:
                        key = f"{camera.owner_user_id}:{camera.id}:{agent.id}"
                        active_agent_keys.add(key)
                        
                        # Start stream for new active agent
                        if key not in _streaming_service._agent_clients:
                            await _streaming_service.start_agent_stream(camera.owner_user_id, camera.id, agent.id)
                
                # Stop streams for inactive agents
                for key in list(_streaming_service._agent_clients.keys()):
                    if key not in active_agent_keys:
                        user_id, camera_id, agent_id = key.split(":", 2)
                        await _streaming_service.stop_agent_stream(user_id, camera_id, agent_id)
            
            except Exception as e:
                print(f"[main] ⚠️  Error monitoring cameras and agents: {e}")

    @application.on_event("startup")
    async def startup_event():
        """
        Start all services when FastAPI starts.
        
        Startup sequence:
        1. Create shared_store (multiprocessing.Manager().dict())
        2. Initialize Event Session Manager (for event video splitting)
        3. Start Runner in background thread → Starts CameraPublisher → Writes frames to shared_store
        4. Wait 3 seconds for CameraPublisher to initialize
        5. Start Streaming Service (AWS mode) → Connects to AWS as camera clients
        6. Start camera monitoring task → Starts streams for active cameras
        """
        # Step 1: Create shared store (shared between Runner and Streaming Service)
        shared_store = get_shared_store()
        print("[main] 📦 Created shared_store for frame sharing")
        
        # Step 2: Initialize Event Session Manager
        from app.utils.event_session_manager import get_event_session_manager
        session_manager = get_event_session_manager()  # This will start background workers
        print("[main] 🎬 Event Session Manager initialized")
        
        # Step 3: Start Runner in background thread
        # Runner will start CameraPublisher which writes frames to shared_store
        def run_runner_with_store():
            run_runner(shared_store)
        
        runner_thread = threading.Thread(target=run_runner_with_store, daemon=True)
        runner_thread.start()
        print("[main] 🚀 Started Agent Runner in background thread")
        print("[main] ⏳ Waiting for CameraPublisher to initialize...")
        
        # Step 4: Wait for CameraPublisher to start and begin publishing frames
        await asyncio.sleep(3)  # Give CameraPublisher time to connect and start publishing
        
        # Step 5: Start Streaming Service (AWS mode)
        # This will connect to AWS signaling server as camera clients
        nonlocal _streaming_service
        _streaming_service = StreamingService(shared_store)
        asyncio.create_task(_streaming_service.start())
        print("[main] 🎥 Started Streaming Service (AWS mode)")
        
        # Step 6: Start camera monitoring task
        asyncio.create_task(monitor_cameras_and_start_streams())
        print("[main] 📊 Started camera monitoring task")
        
        print("[main] ✅ All services started successfully!")

    @application.get("/")
    async def root():
        """Root endpoint - health check."""
        return {
            "status": "running",
            "service": "Agent Camera API",
            "version": "1.0.0",
            "docs": "/docs"
        }

    @application.on_event("shutdown")
    async def shutdown_event():
        """Stop all services when FastAPI shuts down."""
        # Stop Event Session Manager (flush all sessions)
        from app.utils.event_session_manager import get_event_session_manager
        session_manager = get_event_session_manager()
        session_manager.stop()
        print("[main] 🎬 Event Session Manager stopped")
        
        # Stop Streaming Service
        nonlocal _streaming_service
        if _streaming_service:
            await _streaming_service.stop()
        
        print("[main] 🛑 All services stopped")

    @application.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    return application


# Create application instance
app = create_application()

