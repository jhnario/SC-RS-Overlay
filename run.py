"""GUI launcher with file logging instead of a console."""
import os
from pathlib import Path
import sys
import traceback

def main():
    directory=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'SC-RS-Overlay'
    directory.mkdir(parents=True,exist_ok=True)
    # Overwrite each run: do not accumulate logs or screenshots.
    log=(directory/'app.log').open('w',encoding='utf-8',buffering=1)
    sys.stdout=log
    sys.stderr=log
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from app import Overlay
        if os.name=='nt':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Nario.SC.RSReader')
        application=QApplication(sys.argv)
        from PySide6.QtGui import QIcon
        application.setWindowIcon(QIcon(str(Path(__file__).with_name('nave.ico'))))
        overlay=Overlay()
        overlay.show()
        if '--smoke' in sys.argv:
            QTimer.singleShot(2500,overlay.close)
        return application.exec()
    except Exception:
        traceback.print_exc(file=log)
        log.flush()
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,
                'Nao foi possivel abrir o leitor. Veja app.log em %LOCALAPPDATA%\\SC-RS-Overlay.',
                'SC - Leitor RS',16)
        return 1

if __name__=='__main__':
    raise SystemExit(main())

