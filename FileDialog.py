
import os
from textual.screen import ModalScreen
from textual.containers import Grid
from textual.message import Message
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label

class FileDialog(ModalScreen):
    def __init__(self, label_text="Enter file path:", select_type="file", check_exists=False, buttons=None, **kwargs):
        """
        label_text: str, label to display above input
        select_type: 'file', 'folder', or 'both'
        check_exists: bool, if True, check existence before accepting
        buttons: list of (label, id, variant) tuples, e.g. [("OK", "ok", "primary"), ("Cancel", "cancel", "error")]
        """
        super().__init__(**kwargs)
        self.label_text = label_text
        self.select_type = select_type
        self.check_exists = check_exists
        self.buttons = buttons or [("OK", "ok", "primary"), ("Cancel", "cancel", "error")]

    def compose(self) -> "ComposeResult":
        yield Grid(
            Label(self.label_text, id="question"),
            Input(placeholder="/path/to/file-or-folder", id="file-input"),
            *(Button(label, variant=variant, id=btn_id) for label, btn_id, variant in self.buttons),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "ok":
            value = self.query_one("#file-input").value
            if self.check_exists:
                if self.select_type == "file" and not os.path.isfile(value):
                    self.app.bell()
                    self.query_one("#question", Label).update(f"File does not exist: {value}")
                    return
                elif self.select_type == "folder" and not os.path.isdir(value):
                    self.app.bell()
                    self.query_one("#question", Label).update(f"Folder does not exist: {value}")
                    return
                elif self.select_type == "both" and not (os.path.isfile(value) or os.path.isdir(value)):
                    self.app.bell()
                    self.query_one("#question", Label).update(f"File or folder does not exist: {value}")
                    return
            self.dismiss({"value": value, "button": btn_id})
        else:
            self.dismiss({"value": None, "button": btn_id})

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = self.query_one("#file-input").value
        if self.check_exists:
            if self.select_type == "file" and not os.path.isfile(value):
                self.app.bell()
                self.query_one("#question", Label).update(f"File does not exist: {value}")
                return
            elif self.select_type == "folder" and not os.path.isdir(value):
                self.app.bell()
                self.query_one("#question", Label).update(f"Folder does not exist: {value}")
                return
            elif self.select_type == "both" and not (os.path.isfile(value) or os.path.isdir(value)):
                self.app.bell()
                self.query_one("#question", Label).update(f"File or folder does not exist: {value}")
                return
        self.dismiss({"value": value, "button": "ok"})

