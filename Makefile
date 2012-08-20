PREFIX=/usr/local
make: impressiveEditorUI.ui
	pyuic4 -o impressiveEditorUI.py impressiveEditorUI.ui
	lrelease impressive-editor.pro

translate-update: impressiveEditorUI.ui
	pylupdate4 impressive-editor.pro

clean: impressiveEditorUI.py
	rm impressiveEditorUI.py

install: impressiveEditorUI.ui
	install -d ${PREFIX}/share/impressive-editor
	install -d ${PREFIX}/share/impressive-editor/locales
	install -d ${PREFIX}/share/pixmaps
	install -d ${PREFIX}/share/applications

	install impressive-editor.py ${PREFIX}/share/impressive-editor/
	install impressiveEditorUI.py ${PREFIX}/share/impressive-editor/
	install infoscript-tools.py ${PREFIX}/share/impressive-editor/
	install locales/*.qm ${PREFIX}/share/impressive-editor/locales/

	install data/impressive-editor.svg ${PREFIX}/share/pixmaps/
	install data/impressive-editor.desktop ${PREFIX}/share/applications/

	ln -fs ${PREFIX}/share/impressive-editor/impressive-editor.py ${PREFIX}/bin/impressive-editor

uninstall:
	rm -rf ${PREFIX}/share/impressive-editor
	rm -f ${PREFIX}/bin/impressive-editor
	rm -f ${PREFIX}/share/pixmaps/impressive-editor.svg
	rm -f ${PREFIX}/share/applications/impressive-editor.desktop
	rmdir --ignore-fail-on-non-empty ${PREFIX}/share/pixmaps/ ${PREFIX}/share/applications/
