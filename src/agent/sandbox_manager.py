import shutil

import docker
from docker.models.containers import Container
from typing import Tuple, Optional
from pathlib import Path
import os
import time
import subprocess


class SandboxManager:
    """
    Used to start, stop, reset and run instructions in Docker containers
    """
    IMAGE_NAME = "rarat_sandbox_base"
    CONTAINER_NAME = "rarat_agent_sandbox"

    TARGET_CONTAINER_NAME = "rarat_target_server"
    TARGET_IP = "172.28.0.10"
    TARGET_PORT = 3000

    CMD_SHELL = "/bin/bash"

    COMPOSE_FILE = Path("docker_env") / "docker-compose.yml"

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


    def wait_for_target_server(self, timeout: int = 60, interval: int = 2) -> bool:
        """
        Circularly check Target Server open state
        """
        print(f"Waiting for Target Server to respond on {self.TARGET_IP}:{self.TARGET_PORT} (Max {timeout} s)...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            command = f"nc -z -w 1 {self.TARGET_IP} {self.TARGET_PORT}"

            try:
                exit_code, output_bytes = self.container.exec_run(
                    cmd=[self.CMD_SHELL, "-c", command],
                    stdout=True,
                    stderr=True,
                )
                if exit_code == 0:
                    print(f"Target Server {self.TARGET_IP}:{self.TARGET_PORT} is up.")
                    return True
                print(f"Port check failed (Code: {exit_code}). Retrying in {interval}s")

            except Exception as e:
                print(f"Docker network connection error: {e}")

            time.sleep(interval)
        print(f"Error: Target Server is not responding during {timeout} seconds.")
        return False


    def execute_compose_command(self, args:list, compose_dir: Path):
        """
        Execute the docker compose command to start the Sandbox
        """
        command = ['docker', 'compose', '-f', str(self.project_root / self.COMPOSE_FILE)] + args
        print(f"Executing compose command: {' '.join(command)}")

        custom_env = os.environ.copy()
        custom_env['PROJECT_ROOT'] = str(self.project_root)

        try:
            result = subprocess.run(
                command,
                cwd=compose_dir,
                check=True,
                capture_output=True,
                text=True,
                env=custom_env
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Docker compose command error: {e.stderr}")
            raise


    def start_sandbox(self) -> str:
        """
        Start the Sandbox and return its ID(Agent and Target)
        """
        compose_dir = self.project_root / "docker_env"

        print(f"Starting Sandbox {self.IMAGE_NAME} on {self.CONTAINER_NAME}...")
        self.stop_sandbox()

        try:
            self.execute_compose_command(['up', '-d'], compose_dir)
            self.container = self.client.containers.get(self.CONTAINER_NAME)

            if self.container.status != "running":
                raise RuntimeError(f"Agent container started with status: {self.container.status}")

            if not self.wait_for_target_server():
                print(f"Target Server failed. Please check the target server.")

            print(f"Sandbox environment started successfully. Agent ID: {self.container.id[:12]}")
            print(f"Target Server (Juice Shop) IP: http://{self.TARGET_IP}:{self.TARGET_PORT}")
            return self.container.id

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

        # Run command in the container
        try:
            exit_code, output_bytes = self.container.exec_run(
                cmd=[self.CMD_SHELL, "-c", command],
                stdout=True,
                stderr=True,
                tty=False,
                demux=True,
            )

            # Decode the output and clean the format
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
        compose_dir = self.project_root / "docker_env"
        try:
            print(f"Stopping and removing Sandbox container: {self.CONTAINER_NAME}")
            self.execute_compose_command(['down', '--remove-orphans', '-v'], compose_dir)
            print(f"Successfully removed Sandbox container.")
            self.container = None

        except subprocess.CalledProcessError as e:
            if "No resources to remove" not in e.stderr and "not found" not in e.stderr:
                print(f"Failed to remove Sandbox container. Error: {e.stderr.strip()}")
            pass
        except Exception as e:
            print(f"Failed to stop sandbox: {e}")


    def clean_volume_data(self):
        """
        Used to clean up volume data
        to ensure env of the sandbox is clean every experiment time
        """
        if self.volume_path.exists():
            print(f"Cleaning up volume data: {self.volume_path}")
            for item in self.volume_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            print(f"Successfully cleaned up volume data")
        else:
            print(f"Warning:Volume path  {self.volume_path} does not exist for cleaning up.")


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

    manager =SandboxManager(project_root=root)

    try:
        # manager.build_image(dockerfile_path)
        print(f"Starting sandbox...")
        manager.start_sandbox()

        print(f"Target server pinging...")
        code_ping, output_ping = manager.execute_command(f"ping -c 3 {manager.TARGET_IP}")
        print(f"\nPing result: {code_ping}:\n{output_ping.splitlines()[-1]}")

        code_nmap, output_nmap = manager.execute_command(f"nmap -sV -Pn {manager.TARGET_IP}")
        print(f"\nScann Result: {code_nmap}:\n{output_nmap}")

        code_curl, output_curl = manager.execute_command(f"curl -I http://{manager.TARGET_IP}:{manager.TARGET_PORT}/")
        print(f"\nAccess Result (Code:{code_curl}):\n{output_curl.splitlines()[0]}")

    except Exception as e:
        print(f"\nFailed to execute sandbox: {e}")

    finally:
        manager.stop_sandbox()


