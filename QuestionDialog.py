from textual.screen import ModalScreen
from textual.containers import Grid
from textual.app import ComposeResult
from textual.widgets import Button, Label
from textual.binding import Binding

class QuestionDialog(ModalScreen):
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
        height: 8;
        border: solid $accent;
        background: $surface;
    }
        
    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }

    Button {
        width: 100%;
    }
    """

    def __init__(self, label_text="Are you sure?", buttons=None, **kwargs):
        """
        label_text: str, label to display above
        buttons: list of (label, id, variant) tuples, e.g. [("No", "cancel", "error"), ("Yes", "ok", "primary")]
        """
        super().__init__(**kwargs)
        self.label_text = label_text
        self.buttons = buttons or [("No", "cancel", "error"), ("Yes", "ok", "primary")]

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.label_text, id="question"),
            *(Button(label, variant=variant, id=btn_id) for label, btn_id, variant in self.buttons),
            id="dialog"
        )

    def on_mount(self) -> None:
        self.styles.align_horizontal = "center"
        self.styles.align_vertical = "middle"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        self.dismiss({"button": btn_id})

    def action_cancel(self) -> None:
        self.dismiss({"button": "cancel"})