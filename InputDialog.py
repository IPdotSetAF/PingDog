from textual.screen import ModalScreen
from textual.containers import Grid
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label
from textual.binding import Binding

class InputDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
     #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 12;
        border: solid $accent;
        background: $surface;
    }
        
    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    
    Input {
        column-span: 2;
        width: 100%;
    }

    Button {
        width: 100%;
    }
    """

    def __init__(self, label_text="Enter value:", placeholder="", buttons=None, **kwargs):
        """
        label_text: str, label to display above input
        placeholder: str, placeholder text for input
        buttons: list of (label, id, variant) tuples, e.g. [("Cancel", "cancel", "error"), ("OK", "ok", "primary")]
        """
        super().__init__(**kwargs)
        self.label_text = label_text
        self.placeholder = placeholder
        self.buttons = buttons or [("Cancel", "cancel", "error"), ("OK", "ok", "primary")]

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.label_text, id="question"),
            Input(placeholder=self.placeholder, id="input-dialog-input"),
            *(Button(label, variant=variant, id=btn_id) for label, btn_id, variant in self.buttons),
            id="dialog"
        )

    def on_mount(self) -> None:
        self.styles.align_horizontal = "center"
        self.styles.align_vertical = "middle"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        value = self.query_one("#input-dialog-input").value
        if btn_id == "ok":
            self.dismiss({"value": value, "button": btn_id})
        else:
            self.dismiss({"value": None, "button": btn_id})

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = self.query_one("#input-dialog-input").value
        self.dismiss({"value": value, "button": "ok"})

    def action_cancel(self) -> None:
        self.dismiss({"value": None, "button": "cancel"})