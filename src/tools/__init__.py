from .base_tools import get_tools as get_base_tools
from .biochemical_tools import get_tools as get_biochemical_tools
from .ethical_tools import get_tools as get_ethical_tools
#from .unstable_tools import get_tools as get_unstable_tools

def get_all_tools(agent_tools_instance) -> dict:
    all_tools = {}
    all_tools.update(get_base_tools(agent_tools_instance))
    all_tools.update(get_biochemical_tools(agent_tools_instance))
    all_tools.update(get_ethical_tools(agent_tools_instance))
    # all_tools.update(get_unstable_tools(agent_tools_instance))
    return all_tools