import webbrowser

class DocumentationHelper:
    def help_button(self, label: str = None):
        """
        Opens a web page on the documentation site with a search for the given label.

        :param label: The section of the documentation to navigate to. Defaults to 'Workflow'.
        """
        base_url = "https://developer.valvesoftware.com/wiki/Hammer_5_Tools"

        if label is None:
            label = "Workflow"

        # Construct the URL with the label as a fragment identifier
        url = f"{base_url}#{label}"

        try:
            # Open the URL using the webbrowser module
            webbrowser.open(url)
        except Exception as e:
            print(f"Failed to open the URL: {e}")

# Example usage
your_instance = DocumentationHelper()
your_instance.help_button("Loading_Editor")