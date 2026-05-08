import json
from valet.config import config_manager
from groq import Groq
import subprocess
import shutil

class WorkflowEngine:
    def __init__(self):
        self.api_key = config_manager.config.get("groq_api_key")
        self.model = config_manager.config.get("llm_model", "llama-3.3-70b-versatile")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        
        self.dangerous_commands = [
            "rm -rf /", "mkfs", "shutdown", "reboot", "del /s /q c:\\", "format",
            "sudo", "su ", "diskpart"
        ]
        
    def validate_command(self, cmd: str) -> bool:
        cmd_lower = cmd.lower()
        for dangerous in self.dangerous_commands:
            if dangerous in cmd_lower:
                return False
        return True
        
    def generate_workflow(self, prompt: str, previous_workflow=None, modification=None) -> dict:
        if not self.client:
            raise Exception("Groq API key not configured. Cannot generate workflow.")
            
        system_prompt = (
            "You are an expert AI system administrator and developer assistant. "
            "Your job is to generate a safe, step-by-step executable workflow plan based on the user's natural language request. "
            "You must return ONLY a raw JSON object matching this exact structure: "
            '{"title": "...", "risk": "low|medium|high", "summary": "...", "steps": [{"id": 1, "title": "...", "command": "...", "dangerous": false}]} '
            "If the user is asking to modify a previous workflow, apply the modification to the existing plan. "
            "Never execute commands directly. Never use commands like 'rm -rf /' or formatting disks. "
            "Assess the risk. High risk includes deleting large directories, installing global system packages, or modifying system configuration."
        )
        
        user_content = prompt
        if previous_workflow and modification:
            user_content = f"Previous Workflow: {json.dumps(previous_workflow)}\n\nUser Modification Request: {modification}\n\nPlease generate the updated workflow JSON."
            
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        try:
            workflow = json.loads(content)
            # Add strict validation
            for step in workflow.get("steps", []):
                cmd = step.get("command", "")
                if not self.validate_command(cmd):
                    step["command"] = f"echo 'BLOCKED DANGEROUS COMMAND: {cmd}'"
                    step["dangerous"] = True
                    workflow["risk"] = "high"
            return workflow
        except Exception as e:
            raise Exception(f"Failed to parse AI workflow response: {e}\nRaw: {content}")

workflow_engine = WorkflowEngine()
