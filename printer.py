import yaml
from termcolor import colored

# Load theme from YAML file
def load_theme(theme_file):
    with open(theme_file, 'r') as file:
        return yaml.safe_load(file)

def print_colored_yaml(yaml_data, theme):
    def recursive_print(data, level=0):
        indent = '  ' * level
        if isinstance(data, dict):
            for key, value in data.items():
                print(indent + colored(f"{key}:", theme['colors']['key']))
                recursive_print(value, level + 1)
        elif isinstance(data, list):
            for item in data:
                recursive_print(item, level)
        else:
            print(indent + colored(str(data), theme['colors']['value']))

    recursive_print(yaml_data)

if __name__ == "__main__":
    # Input YAML file and theme
    yaml_file = "your_yaml_file.yaml"
    theme_file = "theme.yaml"

    # Load YAML data and theme
    with open(yaml_file, 'r') as file:
        yaml_data = yaml.safe_load(file)

    theme = load_theme(theme_file)

    # Print YAML data with colors
    print_colored_yaml(yaml_data, theme)