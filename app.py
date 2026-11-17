"""Screen-only RS reader. Local OCR, no game hooks or memory access."""
import ctypes
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
from signatures import candidates, parse_rs, DisplaySignal
from html import escape
if os.name == 'nt':
    try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception: pass
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFontDatabase, QFont, QIcon
from PySide6.QtWidgets import (QApplication,QWidget,QLabel,QPushButton,QVBoxLayout,
                              QHBoxLayout,QMessageBox,QFrame,QGraphicsDropShadowEffect)
CONFIG = Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'SC-RS-Overlay' / 'config.json'
STYLE = """
QWidget { background:transparent; color:#a9d8f0; font-family:'Segoe UI'; }
QLabel { background:transparent; }
QFrame#signalCard { background:transparent; border:0; }
QPushButton { background:rgba(12,35,52,190); color:#bdefff; border:1px solid rgba(70,171,224,140);
              padding:6px 8px; border-radius:4px; font-size:12px; }
QPushButton:hover { background:rgba(30,85,113,230); border-color:#80ddff; }
QPushButton#primary { background:rgba(36,130,166,190); color:#e4faff; font-weight:700; }
QPushButton#primary:hover { background:rgba(51,165,201,230); }
QPushButton#help { border:0; background:transparent; color:#72cafa; padding:0; }
QPushButton#help:hover { background:rgba(45,112,150,160); color:white; }
"""

def recognize(engine, frame):
    import cv2
    frame=cv2.resize(frame,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    gray=cv2.normalize(gray,None,0,255,cv2.NORM_MINMAX)
    image=cv2.cvtColor(255-gray,cv2.COLOR_GRAY2BGR)
    image=cv2.copyMakeBorder(image,16,16,16,16,cv2.BORDER_CONSTANT,value=(255,255,255))
    result,_=engine(image,use_cls=False)
    values={parse_rs(row[1]) for row in (result or []) if float(row[2])>=.80}
    values.discard(None)
    return next(iter(values)) if len(values)==1 else None

class Selector(QWidget):
    def __init__(self, callback):
        super().__init__(None,Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        import mss
        with mss.mss() as s:
            self.mon=dict(s.monitors[0])
            shot=s.grab(self.mon)
            self.image=QImage(shot.rgb,shot.width,shot.height,shot.width*3,QImage.Format.Format_RGB888).copy()
        # Convert physical desktop origin/extent to Qt logical coordinates.
        screens=QApplication.screens()
        virtual=screens[0].virtualGeometry()
        self.setGeometry(virtual)
        self.pix=QPixmap.fromImage(self.image)
        self.callback=callback
        self.start=None
        self.end=None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()
        self.activateWindow()
    def paintEvent(self,event):
        p=QPainter(self)
        p.drawPixmap(self.rect(),self.pix)
        p.fillRect(10,10,760,52,QColor('#17212c'))
        p.setPen(QColor('#65d8ff'))
        p.drawText(24,42,'Arraste SOMENTE ao redor dos números RS. ESC cancela.')
        if self.start is not None and self.end is not None:
            p.setPen(QPen(QColor('#65d8ff'),2))
            p.drawRect(QRect(self.start,self.end).normalized())
    def mousePressEvent(self,event):
        self.start=event.position().toPoint()
        self.end=self.start
        self.update()
    def mouseMoveEvent(self,event):
        if self.start is not None:
            self.end=event.position().toPoint()
            self.update()
    def mouseReleaseEvent(self,event):
        if self.start is None:return
        self.end=event.position().toPoint()
        rect=QRect(self.start,self.end).normalized().intersected(self.rect())
        sx=self.image.width()/self.width()
        sy=self.image.height()/self.height()
        w,h=round(rect.width()*sx),round(rect.height()*sy)
        if not (12<=w<=600 and 8<=h<=200):return
        region=dict(left=self.mon['left']+round(rect.x()*sx),
                    top=self.mon['top']+round(rect.y()*sy),width=w,height=h)
        self.close()
        self.callback(region)
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            self.close()
            self.callback(None)

class Overlay(QWidget):
    def __init__(self):
        super().__init__(None,Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.drag_offset=None
        for font_file in ('segoeui.ttf','segoeuib.ttf'):
            font_path = Path(os.environ.get('WINDIR','C:/Windows')) / 'Fonts' / font_file
            if font_path.exists(): QFontDatabase.addApplicationFont(str(font_path))
        QApplication.instance().setFont(QFont('Segoe UI',10))
        self.setWindowTitle('SC • Leitor RS')
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('nave.ico'))))
        self.setFixedSize(300,160)
        self.setWindowOpacity(1.0)
        self.move(40,120)
        self.setStyleSheet(STYLE)
        self.region=None
        try:self.region=json.loads(CONFIG.read_text()).get('region')
        except (OSError,ValueError):pass
        self.paused=True
        self.revision=0
        self.stop=threading.Event()
        self.messages=queue.Queue(maxsize=4)
        self.stable=DisplaySignal()
        self.last_read=time.monotonic()
        layout=QVBoxLayout(self)
        layout.setContentsMargins(8,6,8,8)
        layout.setSpacing(5)
        header=QHBoxLayout()
        brand=QLabel('SC / RS')
        brand.setStyleSheet('font-size:11px; font-weight:700; color:#c4d8ec; letter-spacing:1px;')
        header.addWidget(brand)
        header.addStretch()
        self.status=QLabel('PAUSADO')
        self.status.setStyleSheet('font-size:10px; color:#899db6;')
        header.addWidget(self.status)
        help_button=QPushButton('...')
        help_button.setObjectName('help')
        help_button.setFixedSize(22,22)
        help_button.setToolTip('Mostrar ou recolher controles de leitura')
        help_button.clicked.connect(self.toggle_settings)
        header.addWidget(help_button)
        close_button=QPushButton('×')
        close_button.setObjectName('help')
        close_button.setFixedSize(18,22)
        close_button.setToolTip('Fechar leitor')
        close_button.clicked.connect(self.close)
        header.addWidget(close_button)
        layout.addLayout(header)
        card=QFrame()
        card.setObjectName('signalCard')
        card_layout=QVBoxLayout(card)
        card_layout.setContentsMargins(8,4,8,6)
        card_layout.setSpacing(2)
        caption=QLabel('ASSINATURA RS')
        caption.setStyleSheet('font-size:10px; color:#5999c1; letter-spacing:2px;')
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(caption)
        self.number=QLabel('...')
        self.number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number.setStyleSheet('font-size:34px; font-weight:700; color:#b9eeff;')
        glow=QGraphicsDropShadowEffect(self.number)
        glow.setBlurRadius(14)
        glow.setOffset(0,0)
        glow.setColor(QColor(40,161,255,190))
        self.number.setGraphicsEffect(glow)
        card_layout.addWidget(self.number)
        self.title=QLabel()
        self.title.setStyleSheet('font-size:15px; font-weight:700; color:#99d9fb;')
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        card_layout.addWidget(self.title)
        self.detail=QLabel()
        self.detail.setStyleSheet('font-size:11px; color:#87b9d7;')
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail.setWordWrap(True)
        card_layout.addWidget(self.detail)
        layout.addWidget(card,1)
        self.settings_panel=QWidget()
        settings_layout=QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(0,0,0,0)
        settings_layout.setSpacing(6)
        buttons=QHBoxLayout()
        buttons.setSpacing(8)
        self.area_button=QPushButton('Definir área de leitura')
        self.area_button.setToolTip('Arraste somente ao redor dos números RS. A seleção fica salva.')
        self.area_button.clicked.connect(self.select)
        buttons.addWidget(self.area_button,3)
        self.start_button=QPushButton('Iniciar leitura')
        self.start_button.setObjectName('primary')
        self.start_button.clicked.connect(self.toggle)
        buttons.addWidget(self.start_button,2)
        settings_layout.addLayout(buttons)
        self.area_hint=QLabel()
        self.area_hint.setWordWrap(True)
        self.area_hint.setStyleSheet('font-size:11px; color:#8da3bc;')
        settings_layout.addWidget(self.area_hint)
        layout.addWidget(self.settings_panel)
        self.settings_panel.setVisible(False)
        self.set_message('Pronto para ler' if self.region else 'Configure a leitura')
        self.detail.setText('Abra (...) para iniciar.' if self.region else 'Selecione o número RS na tela do jogo.')
        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setToolTip('Arraste o painel para mover. (...) abre os controles.')
        self.update_controls()
        self.set_expanded(not bool(self.region))
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(50)
        self.thread=threading.Thread(target=self.worker,daemon=True)
        self.thread.start()
    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds=self.rect().adjusted(1,1,-2,-2)
        # Only the background is 60% transparent; HUD text stays bright.
        painter.setBrush(QColor(5,17,28,102))
        painter.setPen(QPen(QColor(51,150,217,95),1))
        painter.drawRoundedRect(bounds,8,8)
        painter.setPen(QPen(QColor(81,191,255,210),1.5))
        w,h=self.width()-4,self.height()-4
        for x,y,dx,dy in ((3,3,1,1),(w,3,-1,1),(3,h,1,-1),(w,h,-1,-1)):
            painter.drawLine(x,y,x+dx*18,y)
            painter.drawLine(x,y,x,y+dy*12)
        painter.setPen(QPen(QColor(47,137,194,90),1))
        painter.drawLine(12,32,self.width()-12,32)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            handle=self.windowHandle()
            if handle and handle.startSystemMove():
                event.accept()
                return
            self.drag_offset=event.globalPosition().toPoint()-self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self,event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint()-self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self,event):
        self.drag_offset=None
        event.accept()

    def send(self,item):
        try:self.messages.put_nowait(item)
        except queue.Full:pass
    def worker(self):
        try:
            import numpy as np
            import mss
            from rapidocr_onnxruntime import RapidOCR
            engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
            with mss.mss() as screen:
                while not self.stop.wait(.08):
                    if self.paused or not self.region:continue
                    revision=self.revision
                    region=dict(self.region)
                    try:
                        frame=np.array(screen.grab(region))[:,:,:3]
                        value=recognize(engine,frame)
                        self.send(('reading',revision,value,time.monotonic()))
                    except Exception as exc:
                        self.send(('error',revision,str(exc),time.monotonic()))
                        self.stop.wait(1)
        except Exception as exc:self.send(('fatal',self.revision,str(exc),time.monotonic()))
    def poll(self):
        while not self.messages.empty():
            kind,revision,value,timestamp=self.messages.get_nowait()
            if kind=='fatal':
                self.paused=True
                self.update_controls()
                self.set_message('OCR INDISPONÍVEL')
                self.detail.setText('Execute Preparar.ps1 novamente.')
                QMessageBox.critical(self,'Falha ao iniciar OCR',value)
            elif revision==self.revision and not self.paused:
                self.last_read=timestamp
                if kind=='error':
                    self.stable=DisplaySignal()
                    self.set_message('FALHA DE CAPTURA')
                    self.detail.setText(value[:60])
                else:
                    confirmed=self.stable.feed(value, timestamp)
                    if confirmed is not None:self.show_value(confirmed)
                    else:
                        self.set_message('AGUARDANDO SINAL' if value is None else 'CONFIRMANDO…')
                        self.detail.setText('Mantenha o código visível na área selecionada.')
        if not self.paused and time.monotonic()-self.last_read>3:
            self.set_message('AGUARDANDO LEITURA')
            self.detail.setText('Sem leitura recente. Aguarde ou ajuste a área.')
            self.stable=DisplaySignal()
    def set_expanded(self,expanded):
        self.settings_panel.setVisible(expanded)
        self.setFixedSize(300,260 if expanded else 160)

    def toggle_settings(self):
        self.set_expanded(self.settings_panel.isHidden())

    def update_controls(self):
        self.start_button.setText('Iniciar' if self.paused else 'Pausar')
        self.status.setText('PAUSADO' if self.paused else 'LENDO TELA')
        self.status.setStyleSheet('font-size:10px; color:'+('#899db6' if self.paused else '#63d5ef')+';')
        self.area_button.setText('Ajustar área de leitura' if self.region else 'Definir área de leitura')
        self.area_hint.setText(('Área salva. ' if self.region else '')+
            'Delimite somente uma vez. Ajuste novamente apenas se o número mudar de posição ou a resolução mudar.')

    def set_message(self,text):
        self.number.setText('...')
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setText(text)
        self.title.setToolTip('')

    def show_value(self,value,test=False):
        matches=[m for m in candidates(value) if m['kind']=='ore' or m['name']=='DEBRIS']
        self.number.setText(f'{value:,}'.replace(',','.'))
        if not matches:
            self.title.setTextFormat(Qt.TextFormat.PlainText)
            self.title.setText('Sinal não identificado')
            self.detail.setText('Sem correspondência em minerais ou salvage.')
        else:
            rows=[]
            for match in matches:
                n=match['count']
                suffix=f'{n} pedra'+('s' if n>1 else '') if match['kind']=='ore' else f'×{n}'
                rows.append('<span style="color:{}">{}</span> <span style="color:#a9bdd0">{}</span>'.format(match['color'],escape(match['name'].upper()),escape(suffix)))
            self.title.setTextFormat(Qt.TextFormat.RichText)
            self.title.setText('<br>'.join(rows))
            label=matches[0]['tier'] if len(matches)==1 else f'{len(matches)} possibilidades'
            label={'Lendario':'Lendário','Epico':'Épico','DEBRIS':'Salvage'}.get(label,label)
            self.detail.setText(label+' · confirme no scan')
        self.title.setToolTip('Possibilidades conforme a tabela fornecida. Sinais sobrepostos podem divergir.')

    def toggle(self):
        if not self.region:return self.select()
        self.paused=not self.paused
        if not self.paused:self.set_expanded(False)
        self.revision+=1
        self.stable=DisplaySignal()
        self.last_read=time.monotonic()
        self.set_message('Leitura pausada' if self.paused else 'Aguardando sinal')
        self.detail.setText('Abra (...) para continuar.' if self.paused else 'Mantenha o RS na área selecionada.')
        self.update_controls()

    def select(self):
        self.paused=True
        self.revision+=1
        self.stable=DisplaySignal()
        self.set_message('Selecionando área')
        self.update_controls()
        self.hide()
        QTimer.singleShot(300,self.selector)
    def selector(self):
        try:self.selection=Selector(self.selected)
        except Exception as exc:
            self.show()
            QMessageBox.critical(self,'Captura',str(exc))
    def selected(self,region):
        self.show()
        saved=True
        if region:
            self.region=region
            try:
                CONFIG.parent.mkdir(parents=True,exist_ok=True)
                CONFIG.write_text(json.dumps({'region':region}),encoding='utf-8')
            except OSError:
                saved=False
            self.set_message('Área salva' if saved else 'Área definida nesta sessão')
            self.detail.setText('Clique em Iniciar leitura.')
        else:
            self.set_message('Seleção cancelada')
            self.detail.setText('Área anterior mantida.' if self.region else 'Clique em Definir área de leitura.')
        self.update_controls()
        if not saved:
            self.area_hint.setText('Não foi possível salvar a área. Ao reabrir, será necessário selecionar novamente.')

    def help(self):
        QMessageBox.information(self,'Como usar',
            '1. Deixe o RS visível no jogo em janela sem bordas.\n'
            '2. Clique em Definir área de leitura e arraste somente ao redor dos números, sem o ícone.\n'
            '3. Clique em Iniciar leitura.\n\n'
            'A área fica salva ao fechar. Só ajuste se mudar a resolução ou a posição do RS.\n'
            'Arraste o painel pelo número ou por uma parte vazia e deixe-a fora da área selecionada.\n\n'
            'Mostra minerais e salvage. As cores indicam a raridade do mineral.\n'
            'Sinais sobrepostos e alterações do jogo podem gerar valores fora da tabela.\n'
            'O resultado aparece na primeira leitura valida. Pequenas falhas de OCR são toleradas por 2,5 segundos.\n'
            'Captura local da tela, sem acesso à memória do jogo.')
    def closeEvent(self,event):
        self.stop.set()
        event.accept()
if __name__=='__main__':
    application=QApplication(sys.argv)
    overlay=Overlay()
    overlay.show()
    sys.exit(application.exec())


