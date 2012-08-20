make: impressiveEditorUI.ui
	pyuic4 -o impressiveEditorUI.py impressiveEditorUI.ui
	lrelease impressive-editor.pro
translate-update: impressiveEditorUI.ui
	pylupdate4 impressive-editor.pro
clean: impressiveEditorUI.py
	rm impressiveEditorUI.py
