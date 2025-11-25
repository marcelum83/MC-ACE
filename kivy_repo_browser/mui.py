import os
import shutil
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from aiclient import AIClient  # your LLM client

# --- LLM setup ---
try:
    # It is recommended to load the API key from a secure source, such as an environment variable.
    # For example: api_key = os.environ.get("AICI_API_KEY")
    client = AIClient(os.environ.get("AICI_API_KEY"), provider="gemini")
except ImportError:
    print("AIClient not found. LLM disabled.")
    client = None

# --- LLM line generator ---
def llm_generate_lines(context_lines, n_lines=3):
    if client is None:
        # fallback dummy
        count = sum(1 for line in context_lines if line.startswith("# AI Line"))
        return [f"# AI Line {count + i + 1}" for i in range(n_lines)]
    prompt = f"Here is some Python code:\n{'\n'.join(context_lines)}\nGenerate {n_lines} additional lines continuing the code logically. Prepend each line with the comment '# AI Line'."
    new_code = client.chat(str(prompt))

    new_code = new_code.replace("```python", "").replace("```", "").strip()
    lines = [line.strip() for line in new_code.splitlines() if line.strip()]
    return lines[:n_lines]

# --- Self-mutating UI ---
class SelfMutateUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        repo_root = os.path.dirname(os.path.realpath(__file__))
        self.files = []
        for filename in os.listdir(repo_root):
            filepath = os.path.join(repo_root, filename)
            if os.path.isfile(filepath) and filename.endswith('.py'):
                self.files.append(filepath)
        self.selected_file = self.files[0] if self.files else None

        self.file_spinner = Spinner(
            text=self.selected_file if self.selected_file else "No .py files",
            values=self.files,
            size_hint_y=0.1
        )
        self.file_spinner.bind(text=self.on_file_select)
        self.add_widget(self.file_spinner)

        self.scroll = ScrollView(size_hint_y=0.7)
        self.label = Label(text="", markup=True, size_hint_y=None)
        self.label.bind(texture_size=self.label.setter('size'))
        self.scroll.add_widget(self.label)
        self.add_widget(self.scroll)

        btn_layout = BoxLayout(size_hint_y=0.2)
        self.btn_commit = Button(text="Commit tmp -> file")
        self.btn_commit.bind(on_press=self.on_commit)
        btn_layout.add_widget(self.btn_commit)

        self.btn_generate = Button(text="Generate Code")
        self.btn_generate.bind(on_press=self.mutate_step)
        btn_layout.add_widget(self.btn_generate)

        self.add_widget(btn_layout)

        self.status_label = Label(text="", size_hint_y=0.1)
        self.add_widget(self.status_label)

        self.prev_lines = []
        self.tmp_name = ""
        self.load_file(self.selected_file)

    def on_file_select(self, spinner, text):
        self.selected_file = text
        self.load_file(text)

    def load_file(self, filename):
        if filename is None:
            self.label.text = "No .py files"
            return
        with open(filename, 'r') as f:
            self.prev_lines = f.read().splitlines()
        self.tmp_name = f"{filename}.tmp"
        if os.path.exists(self.tmp_name):
            with open(self.tmp_name, 'r') as f:
                self.prev_lines = f.read().splitlines()
        self.update_display()

    def mutate_step(self, instance):
        if not self.selected_file:
            return
        # Generate new lines via LLM
        new_lines = llm_generate_lines(self.prev_lines, n_lines=2)
        self.prev_lines.extend(new_lines)
        # write to tmp
        with open(self.tmp_name, 'w') as f:
            f.write("\n".join(self.prev_lines))
        self.update_display()

    def update_display(self, dt=None):
        if not self.prev_lines:
            return
        # Highlight lines from LLM
        text = "\n".join(f"[color=ff00ff]{line}[/color]" if line.startswith("# AI Line") else line
                         for line in self.prev_lines)
        self.label.text = text
        self.scroll.scroll_y = 0

    def on_commit(self, instance):
        if os.path.exists(self.tmp_name):
            shutil.copy(self.tmp_name, self.selected_file)
            os.remove(self.tmp_name)
            self.status_label.text = f"Committed changes to {self.selected_file}"
            self.load_file(self.selected_file)

class SelfMutateApp(App):
    def build(self):
        return SelfMutateUI()

if __name__ == "__main__":
    SelfMutateApp().run()
