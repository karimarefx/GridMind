"""Execute the tutorial with an installed Jupyter kernel (default: python3)."""
import argparse
from pathlib import Path
import nbformat
from nbclient import NotebookClient

parser = argparse.ArgumentParser()
parser.add_argument('--kernel', default='python3')
args = parser.parse_args()
path = Path(__file__).with_name('01_xgboost_forecasting.ipynb').resolve()
notebook = nbformat.read(path, as_version=4)
client = NotebookClient(notebook, timeout=1800, kernel_name=args.kernel,
                        resources={'metadata': {'path': str(path.parents[1])}},
                        on_cell_start=lambda cell, cell_index, **kwargs: print(f'Executing cell {cell_index}', flush=True))
client.execute()
nbformat.write(notebook, path)
print('Executed and saved:', path)
