"""Synthetic OCR + window smoke test. Not a live Star Citizen validation."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from rapidocr_onnxruntime import RapidOCR
from app import recognize,Overlay
from PySide6.QtWidgets import QApplication
engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
for text,expected in [('21,200',21200),('6,370',6370),('3,385',3385)]:
    picture=Image.new('RGB',(85,28),(12,12,12))
    ImageDraw.Draw(picture).text((5,3),text,font=font,fill=(225,220,170))
    value=recognize(engine,np.array(picture)[:,:,::-1].copy())
    assert value==expected,(text,value)
    print('OCR synthetic:',text,'->',value)
blank=np.zeros((28,85,3),dtype=np.uint8)
assert recognize(engine,blank) is None
qt=QApplication([])
widget=Overlay()
widget.show_value(21200,True)
assert 'COPPER' in widget.title.text()
widget.show_value(6370,True)
assert 'STILERON' in widget.title.text()
assert '#ffad24' in widget.title.text()
widget.show_value(12000,True)
assert 'DEBRIS' in widget.title.text()
assert 'ROC' not in widget.title.text() and 'FPS' not in widget.title.text()
assert widget.number.text()=='12.000'
assert widget.height() in (160,260)
widget.set_expanded(False)
widget.grab().save('preview.png')
widget.show_value(6370)
widget.grab().save('preview_hud.png')
widget.set_message('AGUARDANDO SINAL')
assert widget.height() in (160,260)
assert '<span' not in widget.title.text()
widget.close()
print('UI creation and result labels: OK')

