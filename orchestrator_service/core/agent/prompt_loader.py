import os
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import logging

logger = logging.getLogger("prompt_loader")

class PromptLoader:
    """
    Loads and renders Jinja2 prompt templates for different niches.
    Templates are stored in modules/<niche>/prompts/
    """
    
    def __init__(self, modules_path: str = "modules"):
        """
        Initialize the PromptLoader with a base modules directory.
        
        Args:
            modules_path: Path to the modules directory (default: "modules")
        """
        # Get absolute path to modules directory
        base_dir = Path(__file__).parent.parent.parent
        self.modules_path = base_dir / modules_path
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.modules_path)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        logger.info(f"PromptLoader initialized with path: {self.modules_path}")
    
    def load_prompt(self, niche_type: str, template_name: str, context_data: Dict[str, Any]) -> str:
        """
        Load and render a prompt template with context data.
        
        Args:
            niche_type: The niche identifier (e.g., 'dental', 'crm_sales')
            template_name: Name of the template file (e.g., 'base_assistant.txt')
            context_data: Dictionary of variables to inject into the template
            
        Returns:
            Rendered prompt string
            
        Raises:
            TemplateNotFound: If the template doesn't exist
        """
        template_path = f"{niche_type}/prompts/{template_name}"
        
        try:
            template = self.env.get_template(template_path)
            rendered = template.render(**context_data)
            logger.info(f"Successfully loaded prompt: {template_path}")
            return rendered
        except TemplateNotFound:
            logger.error(f"Template not found: {template_path}")
            # Fallback to a basic prompt
            return f"You are a helpful assistant for {niche_type}."
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {e}")
            return f"You are a helpful assistant for {niche_type}."

# Global instance
prompt_loader = PromptLoader()
