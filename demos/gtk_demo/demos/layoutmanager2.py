"""Layout Manager/Transformation
#Keywords: GtkLayoutManager, GskTransform

This demo shows how to use transforms in a nontrivial
way with a custom layout manager. The layout manager places
icons on a sphere that can be rotated using arrow keys.
"""

from PyLiite4 import Gtk

from .demo2widget import demo2_widget_new

window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(parent: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        name = [
            "action-unavailable-symbolic",
            "address-book-new-symbolic",
            "application-exit-symbolic",
            "appointment-new-symbolic",
            "bookmark-new-symbolic",
            "call-start-symbolic",
            "call-stop-symbolic",
            "camera-switch-symbolic",
            "chat-message-new-symbolic",
            "color-select-symbolic",
            "contact-new-symbolic",
            "document-edit-symbolic",
            "document-new-symbolic",
            "document-open-recent-symbolic",
            "document-open-symbolic",
            "document-page-setup-symbolic",
            "document-print-preview-symbolic",
            "document-print-symbolic",
            "document-properties-symbolic",
            "document-revert-symbolic-rtl",
            "document-revert-symbolic",
            "document-save-as-symbolic",
            "document-save-symbolic",
            "document-send-symbolic",
            "edit-clear-all-symbolic",
            "edit-clear-symbolic-rtl",
            "edit-clear-symbolic",
            "edit-copy-symbolic",
            "edit-cut-symbolic",
            "edit-delete-symbolic",
            "edit-find-replace-symbolic",
            "edit-find-symbolic",
            "edit-paste-symbolic",
            "edit-redo-symbolic-rtl",
            "edit-redo-symbolic",
            "edit-select-all-symbolic",
            "edit-select-symbolic",
            "edit-undo-symbolic-rtl",
            "edit-undo-symbolic",
            "error-correct-symbolic",
            "find-location-symbolic",
            "folder-new-symbolic",
            "font-select-symbolic",
            "format-indent-less-symbolic-rtl",
            "format-indent-less-symbolic",
            "format-indent-more-symbolic-rtl",
            "format-indent-more-symbolic",
            "format-justify-center-symbolic",
            "format-justify-fill-symbolic",
            "format-justify-left-symbolic",
            "format-justify-right-symbolic",
            "format-text-bold-symbolic",
            "format-text-direction-symbolic-rtl",
            "format-text-direction-symbolic",
            "format-text-italic-symbolic",
            "format-text-strikethrough-symbolic",
            "format-text-underline-symbolic",
            "go-bottom-symbolic",
            "go-down-symbolic",
            "go-first-symbolic-rtl",
            "go-first-symbolic",
            "go-home-symbolic",
            "go-jump-symbolic-rtl",
            "go-jump-symbolic",
            "go-last-symbolic-rtl",
            "go-last-symbolic",
            "go-next-symbolic-rtl",
            "go-next-symbolic",
            "go-previous-symbolic-rtl",
            "go-previous-symbolic",
            "go-top-symbolic",
            "go-up-symbolic",
            "help-about-symbolic",
            "insert-image-symbolic",
            "insert-link-symbolic",
            "insert-object-symbolic",
            "insert-text-symbolic",
            "list-add-symbolic",
            "list-remove-all-symbolic",
            "list-remove-symbolic",
            "mail-forward-symbolic",
            "mail-mark-important-symbolic",
            "mail-mark-junk-symbolic",
            "mail-mark-notjunk-symbolic",
            "mail-message-new-symbolic",
            "mail-reply-all-symbolic",
            "mail-reply-sender-symbolic",
            "mail-send-receive-symbolic",
            "mail-send-symbolic",
            "mark-location-symbolic",
            "media-eject-symbolic",
            "media-playback-pause-symbolic",
            "media-playback-start-symbolic",
            "media-playback-stop-symbolic",
            "media-record-symbolic",
            "media-seek-backward-symbolic",
            "media-seek-forward-symbolic",
            "media-skip-backward-symbolic",
            "media-skip-forward-symbolic",
            "media-view-subtitles-symbolic",
            "object-flip-horizontal-symbolic",
            "object-flip-vertical-symbolic",
            "object-rotate-left-symbolic",
            "object-rotate-right-symbolic",
            "object-select-symbolic",
            "open-menu-symbolic",
            "process-stop-symbolic",
            "send-to-symbolic",
            "sidebar-hide-symbolic",
            "sidebar-show-symbolic",
            "star-new-symbolic",
            "system-log-out-symbolic",
            "system-reboot-symbolic",
            "system-run-symbolic",
            "system-search-symbolic",
            "system-shutdown-symbolic",
            "system-switch-user-symbolic",
            "tab-new-symbolic",
            "tools-check-spelling-symbolic",
            "value-decrease-symbolic",
            "value-increase-symbolic",
            "view-app-grid-symbolic",
            "view-conceal-symbolic",
            "view-continuous-symbolic",
            "view-dual-symbolic",
            "view-fullscreen-symbolic",
            "view-grid-symbolic",
            "view-list-bullet-symbolic",
            "view-list-ordered-symbolic",
            "view-list-symbolic",
            "view-mirror-symbolic",
            "view-more-horizontal-symbolic",
            "view-more-symbolic",
            "view-paged-symbolic",
            "view-pin-symbolic",
            "view-refresh-symbolic",
            "view-restore-symbolic",
            "view-reveal-symbolic",
            "view-sort-ascending-symbolic",
            "view-sort-descending-symbolic",
            "zoom-fit-best-symbolic",
            "zoom-in-symbolic",
            "zoom-original-symbolic",
            "zoom-out-symbolic",
        ]

        window = Gtk.Window()
        window.set_title("Layout Manager — Transformation")
        window.set_default_size(600, 620)
        window.close_request.connect(close_request)

        widget = demo2_widget_new()

        for i in range(18 * 36):
            child = Gtk.Image.new_from_icon_name(name[i % len(name)])
            child.set_margin_start(4)
            child.set_margin_end(4)
            child.set_margin_top(4)
            child.set_margin_bottom(4)
            widget.add_child(child)

        window.set_child(widget)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
