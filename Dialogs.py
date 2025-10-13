from os import path
from textual.screen import ModalScreen
from textual.containers import Grid, Container
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label, DirectoryTree, ListView, ListItem, Static
from textual.binding import Binding
from textual.reactive import reactive


YES_NO = [("No", "negative", "error"), ("Yes", "positive", "success")]
YES_NO_CANCEL = [("Cancel", "neutral", "primary"), ("No", "negative", "error"), ("Yes", "positive", "success")]
OK_CANCEL = [("Cancel", "neutral", "primary"), ("OK", "positive", "success")]
OK = [("OK", "positive", "success")]
OPEN_CANCEL = [("Cancel", "neutral", "primary"), ("Open", "positive", "success")]


class QuestionDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "neutral", "Cancel", show=False),
    ]

    CSS_PATH="Dialogs.tcss"
    CSS = """
    #dialog {
        padding: 1 2;
        width: 60;
        height: 11;
        border: solid $accent;
        background: $surface;
        border_title_align: center;
    }
    """

    def __init__(self, text="Are you sure?", title="Dialog", buttons=YES_NO, **kwargs):
        """
        text: str, label to display above
        title: str, dialog window title (shown in border)
        buttons: list of (label, id, variant) tuples, e.g. [("Cancel", "cancel", "error"), ("OK", "ok", "primary")]
        """
        super().__init__(**kwargs)
        self.text = text
        self.title = title
        self.buttons = buttons 

    def compose(self) -> ComposeResult:
        container = Container(
            Static(self.text),
            Grid(*(Button(label, variant=variant, id=action) for label, action, variant in self.buttons), classes=f"btn-grid btn-grid-{len(self.buttons)}"),
            id="dialog"
        )
        container.border_title = self.title
        yield container

    def on_mount(self) -> None:
        self.styles.align_horizontal = "center"
        self.styles.align_vertical = "middle"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        if action == "positive":
            self.dismiss(True)
        elif action == "negative":
            self.dismiss(False)
        else:
            self.dismiss(None)

    def action_neutral(self) -> None:
        self.dismiss(None)


class InputDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "neutral", "Cancel", show=False),
    ]

    CSS_PATH="Dialogs.tcss"
    CSS = """
     #dialog {
        padding: 1 2;
        width: 60;
        height: 14;
        border: solid $accent;
        background: $surface;
        border_title_align: center;
    }
    
    Input {
        margin: 1 0;
    }
    """

    def __init__(self, text="Enter value:", title="Dialog", placeholder="", buttons=OK_CANCEL, **kwargs):
        """
        text: str, label to display above input
        title: str, dialog window title (shown in border)
        placeholder: str, placeholder text for input
        buttons: list of (label, action, variant) tuples or use predefined buttons: e.g. OK_CANCEL
        """
        super().__init__(**kwargs)
        self.text = text
        self.title = title
        self.placeholder = placeholder
        self.buttons = buttons

    def compose(self) -> ComposeResult:
        container = Container(
            Static(self.text),
            Input(placeholder=self.placeholder, id="input-dialog-input"),
            Grid(*(Button(label, variant=variant, id=action) for label, action, variant in self.buttons), classes=f"btn-grid btn-grid-{len(self.buttons)}"),
            id="dialog"
        )
        container.border_title = self.title
        yield container

    def on_mount(self) -> None:
        self.styles.align_horizontal = "center"
        self.styles.align_vertical = "middle"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        value = self.query_one("#input-dialog-input").value
        if action == "positive":
            self.dismiss(value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = self.query_one("#input-dialog-input").value
        self.dismiss(value)

    def action_neutral(self) -> None:
        self.dismiss(None)


class FileDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "neutral", "Cancel", show=False),
    ]

    CSS_PATH="Dialogs.tcss"
    CSS = """
    #dialog {
        padding: 1 2 0 2;
        width: 70;
        height: 26;
        border: solid $accent;
        background: $surface;
        border_title_align: center;
    }
        
    #dir-tree {
        height: 11;
        width: 100%;
        border: solid $primary 10%;
        background: $boost;
        overflow: auto;
        margin: 1 0;
    }
    """

    selected_path = reactive("")

    def __init__(self, text="Enter file path:", title="Dialog", select_type="file", check_exists=False, buttons=OPEN_CANCEL, start_path=None, **kwargs):
        """
        text: str, label to display above input
        title: str, dialog window title (shown in border)
        select_type: 'file', 'folder', or 'both'
        check_exists: bool, if True, check existence before accepting
        buttons: list of (label, action, variant) tuples or use predefined buttons: e.g. OK_CANCEL
        start_path: str, initial directory for DirectoryTree
        """
        super().__init__(**kwargs)
        self.text = text
        self.title = title
        self.select_type = select_type
        self.check_exists = check_exists
        self.buttons = buttons 
        self.start_path = start_path or path.expanduser("~")
        if self.select_type == "file" :
            self.placeholder = "/path/to/file"
        elif self.select_type == "folder" :
            self.placeholder = "/path/to/folder"
        elif self.select_type == "both" :
            self.placeholder = "/path/to/file-or-folder"

    def compose(self) -> "ComposeResult":
        container = Container(
            Static(self.text, id="question"),
            DirectoryTree(self.start_path, id="dir-tree"),
            Input(placeholder=self.placeholder, id="file-input"),
            Grid(*(Button(label, variant=variant, id=action) for label, action, variant in self.buttons), classes=f"btn-grid btn-grid-{len(self.buttons)}"),
            id="dialog"
        )
        container.border_title = self.title
        yield container

    def on_mount(self) -> None:
        self.styles.align_horizontal = "center"
        self.styles.align_vertical = "middle"
        # Set input to selected_path if set
        if self.selected_path:
            self.query_one("#file-input", Input).value = self.selected_path

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        # Only allow file selection if select_type is file or both
        if self.select_type in ("file", "both"):
            self.selected_path = event.path
            self.query_one("#file-input", Input).value = str(event.path)

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        # Only allow folder selection if select_type is folder or both
        if self.select_type in ("folder", "both"):
            self.selected_path = event.path
            self.query_one("#file-input", Input).value = str(event.path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        value = self.query_one("#file-input").value
        if action == "positive":
            if self.check_exists:
                if self.select_type == "file" and not path.isfile(value):
                    self.app.bell()
                    self.query_one("#question", Label).update(f"File does not exist: {value}")
                    return
                elif self.select_type == "folder" and not path.isdir(value):
                    self.app.bell()
                    self.query_one("#question", Label).update(f"Folder does not exist: {value}")
                    return
                elif self.select_type == "both" and not (path.isfile(value) or path.isdir(value)):
                    self.app.bell()
                    self.query_one("#question", Label).update(f"File or folder does not exist: {value}")
                    return
            self.dismiss(value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = self.query_one("#file-input").value
        if self.check_exists:
            if self.select_type == "file" and not path.isfile(value):
                self.app.bell()
                self.query_one("#question", Label).update(f"File does not exist: {value}")
                return
            elif self.select_type == "folder" and not path.isdir(value):
                self.app.bell()
                self.query_one("#question", Label).update(f"Folder does not exist: {value}")
                return
            elif self.select_type == "both" and not (path.isfile(value) or path.isdir(value)):
                self.app.bell()
                self.query_one("#question", Label).update(f"File or folder does not exist: {value}")
                return
        self.dismiss(value)

    def action_positive(self) -> None:
        value = self.query_one("#file-input").value
        self.dismiss(value)
    def action_neutral(self) -> None:
        self.dismiss(None)


class OptionDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "neutral", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    CSS = """
    #dialog {
        padding: 1 2;
        width: 60;
        height: 18;
        border: solid $accent;
        background: $surface;
        border_title_align: center;
    }

    ListView {
        margin: 1 0 0 0;
        border: solid $primary 40%;
    }
    """

    def __init__(self, text="Choose an option:", title="Dialog", options=None, **kwargs):
        """
        text: str, label to display above list
        title: str, dialog window title (shown in border)
        options: list of str or (label, value) tuples
        """
        super().__init__(**kwargs)
        self.text = text
        self.title = title
        self.options = options or []

    def compose(self) -> ComposeResult:
        items = []
        for opt in self.options:
            if isinstance(opt, tuple):
                label, value = opt
            else:
                label, value = str(opt), opt
            items.append(ListItem(Label(label), id=f"item-{value}"))

        container = Container(
            Static(self.text),
            ListView(*items, id="options-list"),
            id="dialog"
        )
        container.border_title = self.title
        yield container

    def on_mount(self) -> None:
        self.styles.align_horizontal = "center"
        self.styles.align_vertical = "middle"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # When user selects an item (via enter or click)
        idx = event.index
        value = self._get_option_value(idx)
        self.dismiss(value)

    def action_select(self) -> None:
        idx = self.query_one("#options-list", ListView).index
        value = self._get_option_value(idx)
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _get_option_value(self, idx):
        opt = self.options[idx]
        if isinstance(opt, tuple):
            return opt[1]
        return opt
