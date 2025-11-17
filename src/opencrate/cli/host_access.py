# import asyncio
# import logging
# import os
# import signal
# import time
# from collections import defaultdict, deque
# from contextlib import asynccontextmanager
# from pathlib import Path
# from typing import Any, Dict, Optional

# import daemon
# import uvicorn
# from daemon import pidfile
# from fastapi import FastAPI, Header, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field

# from .app import app as cli_app


# # Request/Response Models
# class CommandRequest(BaseModel):
#     command: str = Field(..., min_length=1, description="Command to execute")
#     timeout: float = Field(default=30.0, ge=1, le=300, description="Timeout in seconds")
#     cwd: Optional[str] = Field(None, description="Working directory")
#     env: Optional[Dict[str, str]] = Field(None, description="Environment variables")


# class CommandResponse(BaseModel):
#     success: bool
#     stdout: Optional[str] = None
#     stderr: Optional[str] = None
#     returncode: Optional[int] = None
#     execution_time: Optional[float] = None
#     error: Optional[str] = None
#     container_name: Optional[str] = None
#     command: str


# # Global state
# class ServerState:
#     def __init__(self, log_dir: Optional[str] = None):
#         self.active_requests = 0
#         self.total_requests = 0
#         self.rate_limiters: Dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=100))
#         self.request_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1000)
#         self.workers: list[asyncio.Task[Any]] = []
#         self.max_concurrent_requests = 10
#         self.start_time = time.time()

#         # Logging setup
#         self.log_dir = Path(log_dir or os.path.expanduser("~/opencrate"))
#         self.log_dir.mkdir(parents=True, exist_ok=True)
#         self.container_loggers: Dict[str, logging.Logger] = {}
#         # Main server logger
#         self.setup_main_logger()

#     def setup_main_logger(self) -> None:
#         """Setup main server logger"""
#         log_file = self.log_dir / "opus_server.log"

#         # Create formatter
#         formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

#         # File handler
#         file_handler = logging.FileHandler(log_file)
#         file_handler.setFormatter(formatter)
#         file_handler.setLevel(logging.INFO)

#         # Console handler (only for non-daemon mode)
#         console_handler = logging.StreamHandler()
#         console_handler.setFormatter(formatter)
#         console_handler.setLevel(logging.INFO)

#         # Root logger
#         root_logger = logging.getLogger()
#         root_logger.setLevel(logging.INFO)
#         root_logger.addHandler(file_handler)

#         self.logger = logging.getLogger(__name__)
#         self.logger.info(f"Opencrate server logger initialized. Log dir: {self.log_dir}")

#     def get_container_logger(self, container_name: str) -> logging.Logger:
#         """Get or create a logger for a specific container"""
#         if container_name not in self.container_loggers:
#             log_file = self.log_dir / f"{container_name}.log"

#             # Create logger
#             logger = logging.getLogger(f"container.{container_name}")
#             logger.setLevel(logging.INFO)

#             # Avoid duplicate handlers
#             if not logger.handlers:
#                 handler = logging.FileHandler(log_file)
#                 formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
#                 handler.setFormatter(formatter)
#                 logger.addHandler(handler)

#                 # Don't propagate to avoid duplicate logs
#                 logger.propagate = False

#             self.container_loggers[container_name] = logger
#             self.logger.info(f"Created logger for container: {container_name}")

#         return self.container_loggers[container_name]

#     def log_command_execution(self, container_name: str, command: str, result: Dict[str, Any], execution_time: float) -> None:
#         """Log command execution to container-specific log"""
#         container_logger = self.get_container_logger(container_name)

#         status = "SUCCESS" if result.get("success") and result.get("returncode") == 0 else "FAILED"

#         container_logger.info(f"[{status}] Command: {command} | Return Code: {result.get('returncode', 'N/A')} | Execution Time: {execution_time:.3f}s")

#         # Log stderr if present
#         if result.get("stderr"):
#             container_logger.warning(f"STDERR: {result['stderr'].strip()}")

#     def check_rate_limit(self, container_name: str) -> bool:
#         """Rate limiting: max 20 requests per minute per container"""
#         now = time.time()
#         container_requests = self.rate_limiters[container_name]

#         # Remove requests older than 1 minute
#         while container_requests and container_requests[0] < now - 60:
#             container_requests.popleft()

#         # Check if under limit
#         if len(container_requests) >= 20:
#             return False

#         container_requests.append(now)
#         return True


# # Global server state
# server_state: Optional[ServerState] = None


# async def command_worker() -> None:
#     """Background worker to process command queue"""
#     assert server_state is not None
#     while True:
#         try:
#             request_data = await server_state.request_queue.get()
#             if request_data is None:  # Shutdown signal
#                 break

#             container_name, command_req, result_future = request_data

#             try:
#                 start_time = time.time()
#                 server_state.active_requests += 1

#                 server_state.logger.info(f"Executing command for {container_name}: {command_req.command[:100]}...")

#                 # Execute command
#                 process = await asyncio.create_subprocess_shell(
#                     command_req.command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=command_req.cwd, env=command_req.env
#                 )

#                 try:
#                     stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=command_req.timeout)

#                     execution_time = time.time() - start_time

#                     result = CommandResponse(
#                         success=True,
#                         stdout=stdout.decode("utf-8"),
#                         stderr=stderr.decode("utf-8"),
#                         returncode=process.returncode,
#                         execution_time=round(execution_time, 3),
#                         container_name=container_name,
#                         command=command_req.command,
#                     )

#                 except asyncio.TimeoutError:
#                     process.kill()
#                     await process.wait()
#                     execution_time = time.time() - start_time

#                     result = CommandResponse(
#                         success=False, error=f"Command timed out after {command_req.timeout} seconds", container_name=container_name, command=command_req.command
#                     )

#                 # Log the execution
#                 server_state.log_command_execution(container_name, command_req.command, result.dict(), execution_time)

#             except Exception as e:
#                 execution_time = time.time() - start_time
#                 result = CommandResponse(success=False, error=str(e), container_name=container_name, command=command_req.command)

#                 server_state.log_command_execution(container_name, command_req.command, result.dict(), execution_time)

#                 server_state.logger.error(f"Command execution failed: {e}")

#             finally:
#                 server_state.active_requests -= 1
#                 if not result_future.cancelled():
#                     result_future.set_result(result)
#                 server_state.request_queue.task_done()

#         except Exception as e:
#             server_state.logger.error(f"Worker error: {e}")


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """App lifespan manager"""
#     assert server_state is not None
#     server_state.logger.info("Starting Opencrate Host Access Server")

#     # Start worker tasks
#     for i in range(server_state.max_concurrent_requests):
#         worker = asyncio.create_task(command_worker())
#         server_state.workers.append(worker)

#     server_state.logger.info(f"✓ Started {len(server_state.workers)} worker tasks")
#     server_state.logger.info(f"Logs directory: {server_state.log_dir}")
#     server_state.logger.info(f"Max concurrent requests: {server_state.max_concurrent_requests}")

#     yield

#     # Shutdown
#     server_state.logger.info("Shutting down server...")

#     # Stop workers
#     for _ in server_state.workers:
#         await server_state.request_queue.put(None)

#     await asyncio.gather(*server_state.workers, return_exceptions=True)
#     server_state.logger.info("✓ Server stopped")


# # FastAPI app
# app = FastAPI(title="Opencrate Host Access Server", description="Background command execution server for dev containers", lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.post("/execute", response_model=CommandResponse)
# async def execute_command(request: CommandRequest, container_name: str = Header(alias="X-Container-Name")):
#     """Execute a command from a dev container"""
#     assert server_state is not None

#     try:
#         # Rate limiting
#         if not server_state.check_rate_limit(container_name):
#             raise HTTPException(status_code=429, detail="Rate limit exceeded (20 requests/minute)")

#         # Check queue capacity
#         if server_state.request_queue.qsize() >= server_state.request_queue.maxsize - 10:
#             raise HTTPException(status_code=503, detail="Server overloaded, try again later")

#         # Create future for result
#         result_future: asyncio.Future[CommandResponse] = asyncio.Future()

#         # Queue the request
#         await server_state.request_queue.put((container_name, request, result_future))
#         server_state.total_requests += 1

#         server_state.logger.info(f"Queued command from {container_name}: {request.command[:50]}...")

#         # Wait for result
#         result = await result_future
#         return result

#     except HTTPException:
#         raise
#     except Exception as e:
#         server_state.logger.error(f"Request processing failed: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     assert server_state is not None
#     return {
#         "status": "healthy",
#         "timestamp": time.time(),
#         "uptime": time.time() - server_state.start_time,
#         "active_requests": server_state.active_requests,
#         "total_requests": server_state.total_requests,
#         "queue_size": server_state.request_queue.qsize(),
#         "log_directory": str(server_state.log_dir),
#         "active_containers": len(server_state.container_loggers),
#     }


# @app.get("/stats")
# async def get_stats():
#     """Detailed server statistics"""
#     assert server_state is not None
#     return {
#         "active_requests": server_state.active_requests,
#         "total_requests": server_state.total_requests,
#         "queue_size": server_state.request_queue.qsize(),
#         "queue_maxsize": server_state.request_queue.maxsize,
#         "worker_count": len(server_state.workers),
#         "max_concurrent": server_state.max_concurrent_requests,
#         "uptime": time.time() - server_state.start_time,
#         "log_directory": str(server_state.log_dir),
#         "active_containers": list(server_state.container_loggers.keys()),
#         "rate_limit_status": {container: len(requests) for container, requests in server_state.rate_limiters.items()},
#     }


# def run_server(host: str, port: int, log_dir: str, max_workers: int) -> None:
#     """Run the server"""
#     # Check if server is already running
#     pid_file = Path(log_dir) / "opus_server.pid"

#     if pid_file.exists():
#         try:
#             with open(pid_file, "r") as f:
#                 pid = int(f.read().strip())

#             # Check if process is actually running
#             os.kill(pid, 0)
#             print(f"✗ Server is already running at {host}:{port}")
#             return

#         except (ValueError, OSError):
#             # PID file exists but process is not running, clean up
#             pid_file.unlink()
#             print("✓ Cleaned up stale PID file")

#     print(f"✓ Starting Opencrate host access server at {host}:{port}")
#     global server_state
#     server_state = ServerState(log_dir)
#     server_state.max_concurrent_requests = max_workers

#     # Run as daemon
#     with daemon.DaemonContext(
#         pidfile=pidfile.TimeoutPIDLockFile(str(pid_file)),
#         working_directory=str(server_state.log_dir),
#         umask=0o002,
#     ):
#         server_state.logger.info(f"Opencrate host access server started as daemon on {host}:{port}")
#         uvicorn.run(app, host=host, port=port, log_level="warning")


# def stop_server(log_dir: str) -> bool:
#     pid_file = Path(log_dir or os.path.expanduser("~/opencrate")) / "opus_server.pid"

#     if not pid_file.exists():
#         print("✗ Server is not running (no PID file found)")
#         return False

#     try:
#         with open(pid_file, "r") as f:
#             pid = int(f.read().strip())

#         os.kill(pid, signal.SIGTERM)

#         for _ in range(10):
#             try:
#                 os.kill(pid, 0)  # Check if process exists
#                 time.sleep(1)
#             except OSError:
#                 break

#         print("✓ Server stopped successfully")
#         return True

#     except (ValueError, OSError, FileNotFoundError) as e:
#         print(f"✗ Failed to stop server: {e}")
#         return False


# def server_status(log_dir: str, port) -> bool:
#     """Check server status"""
#     pid_file = Path(log_dir or os.path.expanduser("~/opencrate")) / "opus_server.pid"

#     if not pid_file.exists():
#         print("Server is not running")
#         return False

#     try:
#         with open(pid_file, "r") as f:
#             pid = int(f.read().strip())

#         os.kill(pid, 0)  # Check if process exists
#         print(f"✓ Server is running (PID: {pid})")
#         print(f"Logs directory: {log_dir}")

#         # Try to get server stats
#         try:
#             import requests

#             response = requests.get(f"http://localhost:{port}/health", timeout=5)
#             if response.status_code == 200:
#                 data = response.json()
#                 print(f"Uptime: {data['uptime']:.1f} seconds")
#                 print(f"Total requests: {data['total_requests']}")
#                 print(f"Active requests: {data['active_requests']}")
#         except Exception:
#             pass

#         return True

#     except OSError:
#         print("✗ Server PID file exists but process is not running")
#         pid_file.unlink()  # Clean up stale PID file
#         return False


# @cli_app.command()
# def host_access(command: str, host: str = "0.0.0.0", port: int = 7315, log_dir: Optional[str] = None, max_workers: int = 10) -> None:
#     """
#     Opencrate Host Access Server main function

#     Args:
#         command: ('start', 'stop', 'status')
#         host: Server host (default: "0.0.0.0")
#         port: Server port (default: 7315)
#         log_dir: Log directory (default: ~/opencrate)
#         max_workers: Maximum concurrent workers (default: 10)
#     """
#     if Path("/.dockerenv").exists():
#         print("✗ '$ oc host-access' command cannot be run inside a container, you must run it on the host machine.")
#         return

#     if command == "start":
#         log_dir = log_dir or os.path.expanduser("~/opencrate")
#         run_server(host, port, log_dir, max_workers)

#     elif command == "stop":
#         log_dir = log_dir or os.path.expanduser("~/opencrate")
#         stop_server(log_dir)

#     elif command == "status":
#         log_dir = log_dir or os.path.expanduser("~/opencrate")
#         server_status(log_dir, port)

#     else:
#         print("Available commands:")
#         print("  start  - Start the server")
#         print("  stop   - Stop the server")
#         print("  status - Check server status")
