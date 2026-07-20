import sys
import os
sys.path.append(os.path.abspath('programa'))

try:
    from demos import demo2_checklist_dia_1
    print("¡Éxito! El archivo se importó correctamente.")
except Exception as e:
    print(f"Error al importar: {e}")