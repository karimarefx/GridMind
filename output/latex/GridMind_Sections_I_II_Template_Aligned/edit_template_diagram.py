"""Fill the supplied university diagram image without redrawing its layout.

Run from the source package: python edit_template_diagram.py
Requires PyMuPDF and Pillow. Edit diagram_labels.json to change text.
"""
from pathlib import Path
import json,hashlib
import pymupdf
from PIL import Image

def fill_diagram(folder):
    folder=Path(folder)
    image_path=folder/'template_diagram_original.png'
    labels=json.loads((folder/'diagram_labels.json').read_text(encoding='utf-8'))
    original=Image.open(image_path).convert('RGB')
    assert original.size==(908,577)
    doc=pymupdf.open();page=doc.new_page(width=908,height=577)
    page.insert_image(page.rect,filename=str(image_path))
    for item in labels:
        rect=pymupdf.Rect(item['rect'])
        rgb=tuple(c/255 for c in original.getpixel(tuple(item['sample'])))
        page.draw_rect(rect,color=None,fill=rgb,overlay=True)
        for font_size in [item.get('font_size',14),13.5,13,12.5,12,11.5]:
            shape=page.new_shape()
            result=shape.insert_textbox(rect,item['text'],fontname='hebo' if item.get('bold') else 'helv',fontsize=font_size,lineheight=1.08,align=1,color=(0,0,0))
            if result>=0:
                shape.commit();break
        else:raise ValueError(('Text does not fit the original box',item))
    out=folder/'selection_figure.pdf';doc.save(out,garbage=4,deflate=True)
    # Original embedded background is retained byte-for-byte after lossless extraction.
    check=pymupdf.open(out)
    assert len(check[0].get_images())==1
    pix=pymupdf.Pixmap(check,check[0].get_images()[0][0])
    assert pix.width==908 and pix.height==577
    print('Filled original template diagram:',out)

if __name__=='__main__':fill_diagram(Path(__file__).resolve().parent)
