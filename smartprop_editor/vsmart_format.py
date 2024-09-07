class VsmartOpen:
    def __init__(self, filename):
        self.filename = filename

    def open_file(self):
        try:
            with open(self.filename, 'r') as file:
                content = file.read()
                print(content)
        except FileNotFoundError:
            print(f"File '{self.filename}' not found.")


class VsmartExport:
    def __init__(self, filename, data):
        self.filename = filename

    def open_file(self):
        try:
            with open(self.filename, 'r') as file:
                content = file.read()
                print(content)
        except FileNotFoundError:
            print(f"File '{self.filename}' not found.")
