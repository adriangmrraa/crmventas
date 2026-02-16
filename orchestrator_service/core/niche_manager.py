import importlib
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("niche_manager")

class NicheManager:
    @staticmethod
    def get_niche_for_tenant(tenant_config: Dict[str, Any]) -> str:
        """
        Determines the niche type from tenant configuration.
        Defaults to 'dental' if not specified.
        """
        return tenant_config.get("niche_type", "crm_sales")

    @staticmethod
    def load_niche_router(app, niche_type: str):
        """
        Dynamically loads and registers the router for the specified niche.
        """
        try:
            # Assumes structure: modules.<niche_type>.routes
            module_path = f"modules.{niche_type}.routes"
            module = importlib.import_module(module_path)
            
            if hasattr(module, "router"):
                # Register with a prefix, checking if it's already registered to avoid duplicates if called multiple times
                # FastAPI doesn't easily let us check registered routers by prefix, 
                # but we can assume this is called once at startup or per-tenant initialization context
                app.include_router(module.router, prefix=f"/niche/{niche_type}", tags=[niche_type])
                logger.info(f"✅ Loaded router for niche: {niche_type}")
            else:
                logger.warning(f"⚠️ Module {module_path} has no 'router' object.")
                
        except ImportError as e:
            logger.error(f"❌ Failed to load niche router for {niche_type}: {e}")
        except Exception as e:
            logger.error(f"❌ Error loading niche router {niche_type}: {e}")

    @staticmethod
    def get_niche_tools(niche_type: str, tenant_id: int) -> List[Any]:
        """
        Loads tools specific to the niche.
        """
        try:
            module_path = f"modules.{niche_type}.tools"
            module = importlib.import_module(module_path)
            
            if hasattr(module, "get_tools"):
                return module.get_tools(tenant_id)
            elif hasattr(module, "register_tools"):
                 # Some modules might use a register function (like dental)
                 # We might need to standardize this interface.
                 # For now, let's assume we want a list of tool functions/definitions
                 logger.warning(f"⚠️ Module {module_path} uses 'register_tools' but 'get_tools' is expected for direct retrieval.")
                 return []
            else:
                logger.warning(f"⚠️ Module {module_path} has no 'get_tools' function.")
                return []
                
        except ImportError:
            logger.warning(f"⚠️ No tools module found for niche: {niche_type}")
            return []
        except Exception as e:
            logger.error(f"❌ Error loading tools for {niche_type}: {e}")
            return []
