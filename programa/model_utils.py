"""
Módulo de utilidades del modelo (Área: LLM y Benchmark).

Responde a: ¿Cómo se consultan y validan esos modelos?
Proporciona el puente de lógica sin duplicidades de constantes ni lógica compleja.
"""

from programa.model_registry import MODELS


def obtener_modelo(model_key: str) -> dict:
    """
    Devuelve una copia de la configuración del modelo solicitado.
    """
    if model_key in MODELS:
        return MODELS[model_key].copy()

    raise KeyError(
        f"Modelo desconocido o no autorizado: {model_key}"
    )


def listar_modelos_benchmark() -> list[str]:
    """
    Devuelve las claves activas del benchmark oficial.
    """
    return [
        model_key
        for model_key, model_config in MODELS.items()
        if model_config.get("enabled", False)
    ]


def validar_modelos_benchmark() -> None:
    """
    Comprueba que el benchmark oficial cumple sus reglas mínimas.
    Asegura que tengamos exactamente dos modelos del mismo proveedor activos.
    """
    modelos_activos = [
        model_config
        for model_config in MODELS.values()
        if model_config.get("enabled", False)
    ]

    if len(modelos_activos) != 2:
        raise ValueError(
            "El benchmark oficial debe contener exactamente "
            "dos modelos activos."
        )

    proveedores = {
        model_config["provider"]
        for model_config in modelos_activos
    }

    if len(proveedores) != 1:
        raise ValueError(
            "Los modelos oficiales deben pertenecer "
            "al mismo proveedor."
        )

    for model_config in modelos_activos:
        if not model_config.get("model_id"):
            raise ValueError(
                "Todos los modelos deben tener un model_id."
            )
            

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    print("📋 Listando modelos activos para el benchmark...")
    try:
        validar_modelos_benchmark()
        print(f"✅ Validación correcta. Modelos oficiales: {listar_modelos_benchmark()}")
    except Exception as e:
        print(f"❌ Error en la validación: {e}")