import docker
from docker.models.containers import Container
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import os
import time


class SandboxManager:
    """
    Used to start, stop, reset and run instructions in Docker containers
    """
    IMAGE_NAME = "rarat_sandbox_base"
    CONTAINER_NAME = "rarat_agent_sandbox"
    CMD_SHELL = "/bin/bash"

    def __init__(self, project_root: Path):
        """
        Initialize the SandboxManager class
        """
        try:
            self.client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
            self.client.ping()
            print("Docker client connected successfully.")
        except Exception as e:
            print("Error: Docker client failed to connect. Please check Docker running state.")
            raise e

        self.container: Optional[Container] = None
        self.project_root = project_root

        #Mount 'project_root/sandbox_data' to container's '/sandbox'
        self.volume_path = self.project_root / "sandbox_data"
        self.volume_path.mkdir(exist_ok=True)
        self.volumes: Dict[str, Dict[str, str]] = {
            str(self.volume_path.resolve()): {
                "bind": "/sandbox",
                "mode": "rw",
            }
        }


    def build_image(self, dockerfile_path: Path):
        """
        Build the Docker image
        """
        print(f"Building Docker image {self.IMAGE_NAME} from {dockerfile_path.parent}...")
        try:
            self.client.images.build(
                path=str(dockerfile_path.parent),
                dockerfile=dockerfile_path.name,
                tag=self.IMAGE_NAME,
                rm=True,
            )
            print(f"Image {self.IMAGE_NAME} built successfully.")
        except docker.errors.BuildError as e:
            print(f"Build Error: {e}")
            raise


    def start_sandbox(self) -> str:
        """
        Start the Sandbox and return its ID
        """
        print(f"Starting Sandbox {self.IMAGE_NAME} on {self.CONTAINER_NAME}...")
        self.stop_sandbox()

        try:
            self.container = self.client.containers.run(
                image=self.IMAGE_NAME,
                name=self.CONTAINER_NAME,
                detach=True,
                tty=True,
                volumes=self.volumes,
                network_mode="none",
            )
            time.sleep(2)
            print(f"Sandbox {self.CONTAINER_NAME} started successfully.")
            return self.container.id
        except docker.errors.ImageNotFound:
            raise EnvironmentError(f"Docker image {self.IMAGE_NAME} not found.")
        except Exception as e:
            print(f"Error starting sandbox: {e}")
            self.stop_sandbox()
            raise


    def execute_command(self, command: str) -> Tuple[int, str]:
        """
        Execute a bash command and return its Exit Code, Output String
        """
        if not self.container:
            raise EnvironmentError(f"Container {self.CONTAINER_NAME} not found.")

        print(f"Executing in container: '{command}'")

        try:
            exit_code, output_bytes = self.container.exec_run(
                cmd=[self.CMD_SHELL, "-c", command],
                stdout=True,
                stderr=True,
                tty=False,
                demux=True,
            )

            stdout_raw = output_bytes[0]
            stderr_raw = output_bytes[1]
            stdout_output = stdout_raw.decode('utf-8', errors='ignore').strip() if stdout_raw else ""
            stderr_output = stderr_raw.decode('utf-8', errors='ignore').strip() if stderr_raw else ""

            full_output = stdout_output
            if stderr_output:
                full_output += f"\n[STDERR]: {stderr_output}"
            return exit_code, full_output

        except Exception as e:
            return 1,f"Execution failed due to Docker error: {e}"


    def stop_sandbox(self):
        """
        Stop and remove the Sandbox container
        """
        try:
            container_to_stop = None
            if self.container:
                container_to_stop = self.container
            else:
                container_to_stop = self.client.containers.get(self.CONTAINER_NAME)
            if container_to_stop:
                print(f"Stopping and removing container {self.CONTAINER_NAME}...")
                container_to_stop.stop(timeout=5)
                container_to_stop.remove(v=True)
                print(f"Successfully removed Sandbox container {self.CONTAINER_NAME}.")

        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"Failed to stop sandbox: {e}")


    def get_safe_path(self, container_path: str) -> str:
        """
        Mapping the container mount point path to host mount space
        """
        if container_path.startswith('/sandbox'):
            return str(self.volume_path / container_path.replace('/sandbox/', ''))

        return container_path


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    root = current_dir.parent.parent

    dockerfile_path = root / "docker_env" / "Dockerfile"
    manager =SandboxManager(project_root=root)

    try:
        # manager.build_image(dockerfile_path)
        manager.start_sandbox()
        code, output = manager.execute_command("echo 'Hello from Agent!' > /sandbox/test_output.txt && ls -l /sandbox")
        print(f"\nExecution Result (Code:{code}):\n{output}")
        local_file_path = manager.get_safe_path("/sandbox/test_output.txt")
        if Path(local_file_path).exists():
            print(f"\nLocal File Check: {local_file_path} exists and content is:")
            print(Path(local_file_path).read_text())

    except Exception as e:
        print(f"\nFailed to execute sandbox: {e}")

    finally:
        manager.stop_sandbox()


