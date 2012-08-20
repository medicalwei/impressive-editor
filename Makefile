DESTDIR=
PREFIX=/usr
INSTALL_DIR=$(DESTDIR)/usr

make: impressiveEditorUI.ui impressive-editor.pro
	pyuic4 -o impressiveEditorUI.py impressiveEditorUI.ui
	lrelease impressive-editor.pro

translate-update: impressiveEditorUI.ui
	pylupdate4 impressive-editor.pro

clean:
	rm -f impressiveEditorUI.py
	rm -f locales/*.qm

install: impressiveEditorUI.py
	mkdir -p ${INSTALL_DIR}/share/impressive-editor
	mkdir -p ${INSTALL_DIR}/share/impressive-editor/locales
	mkdir -p ${INSTALL_DIR}/share/pixmaps
	mkdir -p ${INSTALL_DIR}/share/applications
	mkdir -p ${INSTALL_DIR}/share/man/man1/
	mkdir -p ${INSTALL_DIR}/bin

	install -m755 impressive-editor.py ${INSTALL_DIR}/share/impressive-editor/
	install -m644 impressiveEditorUI.py ${INSTALL_DIR}/share/impressive-editor/
	install -m644 infoscript-tools.py ${INSTALL_DIR}/share/impressive-editor/
	install -m644 locales/*.qm ${INSTALL_DIR}/share/impressive-editor/locales/

	install -m644 data/impressive-editor.svg ${INSTALL_DIR}/share/pixmaps/
	install -m644 data/impressive-editor.desktop ${INSTALL_DIR}/share/applications/
	install -m644 data/impressive-editor.1 ${INSTALL_DIR}/share/man/man1/

	ln -fs ${PREFIX}/share/impressive-editor/impressive-editor.py ${INSTALL_DIR}/bin/impressive-editor

uninstall:
	rm -rf ${PREFIX}/share/impressive-editor
	rm -f ${PREFIX}/bin/impressive-editor
	rm -f ${PREFIX}/share/pixmaps/impressive-editor.svg
	rm -f ${PREFIX}/share/applications/impressive-editor.desktop
	rm -f ${PREFIX}/share/man/man1/impressive-editor.1
	rmdir --ignore-fail-on-non-empty -p ${PREFIX}/share/pixmaps/ ${PREFIX}/share/applications/ ${PREFIX}/bin/ ${PREFIX}/share/man/man1/
