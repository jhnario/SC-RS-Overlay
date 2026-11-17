import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Qt
import app

class QuietOverlay(app.Overlay):
    def worker(self): pass

class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.config=Path(self.tmp.name)/'config.json'
        self.patch=patch.object(app,'CONFIG',self.config)
        self.patch.start()
        self.w=QuietOverlay()
    def tearDown(self):
        self.w.close()
        self.patch.stop()
        self.tmp.cleanup()
    def test_results_and_controls(self):
        self.w.show_value(6370)
        self.assertEqual(self.w.number.text(),'6.370')
        self.assertIn('STILERON',self.w.title.text())
        self.assertIn('#ffad24',self.w.title.text())
        self.w.show_value(12000)
        self.assertIn('DEBRIS',self.w.title.text())
        self.assertNotIn('ROC',self.w.title.text())
        self.assertNotIn('FPS',self.w.title.text())
        self.w.show_value(9000)
        self.assertEqual(self.w.number.text(),'9.000')
        self.assertNotIn('FPS',self.w.title.text())
        self.assertFalse(any(b.text()=='Teste' for b in self.w.findChildren(QPushButton)))
    def test_save_reload_pause_and_cancel(self):
        region=dict(left=100,top=100,width=80,height=25)
        self.w.selected(region)
        self.assertEqual(json.loads(self.config.read_text())['region'],region)
        second=QuietOverlay()
        self.assertEqual(second.region,region)
        self.assertIn('salva',second.area_hint.text())
        second.close()
        self.w.toggle()
        self.assertFalse(self.w.paused)
        self.assertEqual(self.w.start_button.text(),'Pausar')
        self.w.toggle()
        self.assertTrue(self.w.paused)
        self.assertEqual(self.w.number.text(),'...')
        self.w.selected(None)
        self.assertEqual(self.w.region,region)
    def test_compact_and_transparent(self):
        self.w.set_expanded(False)
        self.assertEqual((self.w.width(),self.w.height()),(300,160))
        self.assertTrue(self.w.settings_panel.isHidden())
        self.assertAlmostEqual(self.w.windowOpacity(),1.0,places=2)
        self.assertTrue(self.w.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(self.w.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertFalse(self.w.windowIcon().isNull())
        self.assertTrue(any(b.toolTip()=='Fechar leitor' for b in self.w.findChildren(QPushButton)))
        self.w.toggle_settings()
        self.assertFalse(self.w.settings_panel.isHidden())
        self.assertEqual(self.w.height(),260)
        self.w.toggle_settings()
        self.assertEqual(self.w.height(),160)

    def test_first_read_updates_overlay(self):
        self.w.paused=False
        for value, expected in ((6370,'6.370'),(16960,'16.960')):
            self.w.send(('reading',self.w.revision,value,time.monotonic()))
            self.w.poll()
            self.assertEqual(self.w.number.text(),expected)

    def test_gap_hold_and_stale_clear(self):
        self.w.paused=False
        t=time.monotonic()
        for value in (16960,16960,None,None):
            self.w.send(('reading',self.w.revision,value,t))
        self.w.poll()
        self.assertEqual(self.w.number.text(),'16.960')
        self.w.last_read=t-4
        self.w.poll()
        self.assertEqual(self.w.number.text(),'...')

if __name__=='__main__':unittest.main()
