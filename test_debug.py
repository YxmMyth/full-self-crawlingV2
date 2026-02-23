import asyncio
import sys
import os
from pathlib import Path

# Windows console UTF-8 fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

# Add project root to path
project_root = Path('.')
sys.path.insert(0, str(project_root))

# Import the graph module fresh
import importlib
import src.agent.graph as graph_module
importlib.reload(graph_module)

# Monkey patch soal_node - use the correct attribute name!
original_soal_node = graph_module.soal_node

async def debug_soal_node(state):
    print('[DEBUG] soal_node called, current code length: {}'.format(len(state.get('generated_code', ''))))
    print('[DEBUG] soal_iteration: {}'.format(state.get('sool_iteration', 0)))
    try:
        result = await original_soal_node(state)
        print('[DEBUG] soal_node completed, new code length: {}'.format(len(result.get('generated_code', ''))))
        if result.get('last_error'):
            print('[DEBUG] soal_node last_error: {}'.format(result.get('last_error', '')[:100]))
        return result
    except Exception as e:
        print('[DEBUG] soal_node exception: {}'.format(e))
        import traceback
        traceback.print_exc()
        raise

graph_module.soal_node = debug_soal_node

# Now import SiteAgent which will use the patched graph
from src.agent import SiteAgent

async def test_simple_site():
    '''Test quotes.toscrape.com'''

    task = {
        'site_url': 'http://quotes.toscrape.com/',
        'user_goal': 'Extract quotes with author and tags'
    }

    print('='*70)
    print('  Testing: {}'.format(task['site_url']))
    print('='*70)

    agent = SiteAgent()

    result = await agent.run(task)

    print('')
    print('[Result Summary]')
    print('  Success: {}'.format(result.get('success', False)))
    print('  Data count: {}'.format(len(result.get('data', []))))

    final_state = result.get('final_state', {})
    print('  Stage: {}'.format(result.get('stage', 'unknown')))
    print('  SOOAL iterations: {}'.format(final_state.get('sool_iteration', 0)))
    print('  Generated code length: {}'.format(len(final_state.get('generated_code', ''))))

    return result

# Run test
result = asyncio.run(test_simple_site())
