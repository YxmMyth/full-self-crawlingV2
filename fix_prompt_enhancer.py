# Fix the prompt_enhancer.py f-string issue
with open('src/agent/prompt_enhancer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Revert previous changes
content = content.replace('{{stealth_config}}', '{stealth_config}')
content = content.replace('{{code_extraction_guide}}', '{code_extraction_guide}')
content = content.replace('{{url}}', '{url}')

# The real fix: escape the braces in the config values by doubling them
# This way when they're substituted into the f-string, they won't be interpreted as format specifiers
content = content.replace('"--disable-blink-features=AutomationControlled"', '"--disable-blink-features=AutomationControlled"')

# Actually, the simpler fix is to change the template to not use f-string for the code example part
# Let's find the problematic section and fix it

# Find the section from "return f\"\"\"你是一个Web爬虫" to the end and change the approach
# The issue is that the template contains {stealth_config} which gets substituted with a value containing {}
# We need to escape the {} in the substituted value

# Simpler fix: just double the braces in the _get_stealth_config_text function return values
old_configs = '''    configs = {
        "none": """headless=True, args=[]""",
        "low": """headless=True, args=["--disable-blink-features=AutomationControlled"]""",
        "medium": """headless=False, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]""",
        "high": """headless=False, args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security", "--disable-dev-shm-usage"]""",
    }'''

new_configs = '''    configs = {
        "none": """headless=True, args=[]""",
        "low": """headless=True, args=['--disable-blink-features=AutomationControlled']""",
        "medium": """headless=False, args=['--disable-blink-features=AutomationControlled', '--no-sandbox']""",
        "high": """headless=False, args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-web-security', '--disable-dev-shm-usage']""",
    }'''

content = content.replace(old_configs, new_configs)

# Also fix the viewport issue by changing {} to {{}}
content = content.replace('viewport={"width": 1920, "height": 1080}', 'viewport="{{"width": 1920, "height": 1080}}"')

with open('src/agent/prompt_enhancer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed prompt_enhancer.py')
