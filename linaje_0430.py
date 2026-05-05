# linaje_0430.py
# Consulta el linaje de campos desde MongoDB Atlas (colección linaje_0430)
# El diccionario completo está en la base de datos — cargado con cargar_linaje.py

import os
import re
import unicodedata
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
_mongo = MongoClient(os.getenv("MONGO_URI"))
_db    = _mongo[os.getenv("DB_NAME")]
_col   = _db["linaje_0430"]

# Mapa número → clave (para búsqueda rápida sin ir a Mongo)
NUMERO_CAMPO_0430 = {
    1: "PERIODO", 2: "CLAVE_INSTITUCION", 3: "REPORTE",
    4: "ID_ACREDITADO", 5: "NOMBRE", 6: "RFC", 7: "CURP",
    8: "LOCALIDAD", 9: "MUNICIPIO", 10: "ESTADO",
    11: "NACIONALIDAD", 12: "ACT_ECONOMICA", 13: "GPO_RIESGO",
    14: "ACRED_RELACIONADO", 15: "TPO_CARTERA", 16: "TPO_ANEXO",
    17: "NUM_SIC", 18: "LEI", 19: "ID_LINEACREDITO",
    20: "ID_CREDITO_CNBV", 21: "ID_LINEA_GRUPAL_CNBV", 22: "DESTINO",
    23: "MONTO_LINEA_VALORIZADO", 24: "MONTO_LINEA_MONEDA_ORIGEN",
    25: "FECHA_OTORGAMIENTO", 26: "FECHA_VENCIMIENTO", 27: "FECHA_MAXIMA_DISP",
    28: "FORMA_DISP", 29: "REVOCABLE", 30: "PRELACION",
    31: "PRC_PART_FEDERALES", 32: "CVE_INST_OTORGANTE", 33: "TPO_ALTA",
    34: "MONEDA", 35: "TPO_TASA", 36: "DIF_TASA", 37: "OPER_DIF_TASA",
    38: "FREC_REVISION_TASA", 39: "PERIODICIDAD_CAPITAL", 40: "PERIODICIDAD_INTERES",
    41: "MESES_GRACIA_CAPITAL", 42: "MESES_GRACIA_INTERES",
    43: "COMISION_APERTURA_TASA", 44: "COMISION_APERTURA_MONTO",
    45: "COMISION_DISPOSICION_TASA", 46: "COMISION_DISPOSICION_MONTO",
    47: "CAT", 48: "MONTO_LINEA_SIN_ACCESORIOS", 49: "MONTO_PRIMAS_ANUALES",
    50: "LOCALIDAD_DESTINO", 51: "MUNICIPIO_DESTINO", 52: "ESTADO_DESTINO",
    53: "ACT_ECONOMICA_DESTINO",
}

# Alias para búsqueda por nombre
ALIAS_0430 = {
    "reporte": "REPORTE", "periodo": "PERIODO",
    "clave institucion": "CLAVE_INSTITUCION",
    "id acreditado": "ID_ACREDITADO", "nombre": "NOMBRE", "nombre cnbv": "NOMBRE",
    "rfc": "RFC", "rfc del acreditado": "RFC",
    "curp": "CURP", "curp del acreditado": "CURP",
    "localidad": "LOCALIDAD", "localidad del domicilio del acreditado": "LOCALIDAD",
    "municipio": "MUNICIPIO", "municipio del domicilio del acreditado": "MUNICIPIO",
    "estado": "ESTADO", "estado del domicilio del acreditado": "ESTADO",
    "nacionalidad": "NACIONALIDAD", "nacionalidad del acreditado": "NACIONALIDAD",
    "actividad economica": "ACT_ECONOMICA", "act economica": "ACT_ECONOMICA",
    "actividad economica del acreditado": "ACT_ECONOMICA",
    "grupo de riesgo": "GPO_RIESGO", "gpo riesgo": "GPO_RIESGO", "grupo de riesgo comun": "GPO_RIESGO",
    "acreditado relacionado": "ACRED_RELACIONADO",
    "tipo de cartera": "TPO_CARTERA", "tpo cartera": "TPO_CARTERA",
    "tipo de anexo": "TPO_ANEXO", "tpo anexo": "TPO_ANEXO",
    "num sic": "NUM_SIC", "numero sic": "NUM_SIC",
    "numero de consulta realizada a la sociedad de informacion crediticia": "NUM_SIC",
    "lei": "LEI", "clave lei": "LEI",
    "id linea credito": "ID_LINEACREDITO", "identificador del credito asignado por la institucion": "ID_LINEACREDITO",
    "id credito cnbv": "ID_CREDITO_CNBV", "identificador credito": "ID_CREDITO_CNBV",
    "identificador del credito asignado metodologia cnbv": "ID_CREDITO_CNBV",
    "id linea grupal": "ID_LINEA_GRUPAL_CNBV",
    "destino": "DESTINO", "destino del credito": "DESTINO",
    "monto linea valorizado": "MONTO_LINEA_VALORIZADO", "monto valorizado": "MONTO_LINEA_VALORIZADO",
    "monto de la linea de credito autorizado valorizado en pesos": "MONTO_LINEA_VALORIZADO",
    "monto linea moneda origen": "MONTO_LINEA_MONEDA_ORIGEN", "monto autorizado": "MONTO_LINEA_MONEDA_ORIGEN",
    "fecha otorgamiento": "FECHA_OTORGAMIENTO", "fecha de otorgamiento de la linea de credito": "FECHA_OTORGAMIENTO",
    "fecha vencimiento": "FECHA_VENCIMIENTO", "fecha de vencimiento de la linea de credito": "FECHA_VENCIMIENTO",
    "fecha maxima disposicion": "FECHA_MAXIMA_DISP", "fecha maxima disp": "FECHA_MAXIMA_DISP",
    "fecha maxima para disponer de los recursos": "FECHA_MAXIMA_DISP",
    "forma disposicion": "FORMA_DISP", "forma disp": "FORMA_DISP", "forma de la disposicion": "FORMA_DISP",
    "revocable": "REVOCABLE", "linea de credito revocable o irrevocable": "REVOCABLE",
    "prelacion": "PRELACION", "prelacion de pago credito preferente o subordinado": "PRELACION",
    "participaciones federales": "PRC_PART_FEDERALES", "prc part federales": "PRC_PART_FEDERALES",
    "clave institucion otorgante": "CVE_INST_OTORGANTE", "cve inst otorgante": "CVE_INST_OTORGANTE",
    "tipo alta": "TPO_ALTA", "tpo alta": "TPO_ALTA", "tipo de alta del credito": "TPO_ALTA",
    "moneda": "MONEDA", "moneda de la linea de credito": "MONEDA",
    "tipo tasa": "TPO_TASA", "tpo tasa": "TPO_TASA", "tipo de tasa de interes de la linea de credito": "TPO_TASA",
    "diferencial tasa": "DIF_TASA", "dif tasa": "DIF_TASA",
    "operador diferencial": "OPER_DIF_TASA", "oper dif tasa": "OPER_DIF_TASA",
    "frecuencia revision tasa": "FREC_REVISION_TASA", "frec revision tasa": "FREC_REVISION_TASA",
    "periodicidad capital": "PERIODICIDAD_CAPITAL", "periodicidad pagos de capital": "PERIODICIDAD_CAPITAL",
    "periodicidad interes": "PERIODICIDAD_INTERES", "periodicidad pagos de intereses": "PERIODICIDAD_INTERES",
    "meses gracia capital": "MESES_GRACIA_CAPITAL", "numero de meses de gracia para amortizar capital": "MESES_GRACIA_CAPITAL",
    "meses gracia interes": "MESES_GRACIA_INTERES", "numero de meses de gracia para pago de intereses": "MESES_GRACIA_INTERES",
    "comision apertura tasa": "COMISION_APERTURA_TASA", "comision de apertura del credito tasa": "COMISION_APERTURA_TASA",
    "comision apertura monto": "COMISION_APERTURA_MONTO", "comision de apertura del credito monto": "COMISION_APERTURA_MONTO",
    "comision disposicion tasa": "COMISION_DISPOSICION_TASA",
    "comision disposicion monto": "COMISION_DISPOSICION_MONTO",
    "cat": "CAT", "costo anual total cat": "CAT",
    "monto linea sin accesorios": "MONTO_LINEA_SIN_ACCESORIOS",
    "monto primas anuales": "MONTO_PRIMAS_ANUALES", "monto de las primas anuales de todos los seguros obligatorios": "MONTO_PRIMAS_ANUALES",
    "localidad destino": "LOCALIDAD_DESTINO", "localidad en donde se destinara el credito": "LOCALIDAD_DESTINO",
    "municipio destino": "MUNICIPIO_DESTINO", "municipio en donde se destinara el credito": "MUNICIPIO_DESTINO",
    "estado destino": "ESTADO_DESTINO", "estado en donde se destinara el credito": "ESTADO_DESTINO",
    "actividad economica destino": "ACT_ECONOMICA_DESTINO", "act economica destino": "ACT_ECONOMICA_DESTINO",
    "actividad economica a la que se destinara el credito": "ACT_ECONOMICA_DESTINO",
}


def normalizar(texto):
    texto = texto.lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto.replace('(', '').replace(')', '').replace('  ', ' ')


def obtener_doc(clave, reporte="0430"):
    """Obtiene el documento completo de MongoDB para un campo"""
    return _col.find_one({"reporte": reporte, "clave": clave}, {"_id": 0})


def buscar_linaje(texto, reporte="0430"):
    """Busca el linaje de un campo — devuelve (clave, linaje_texto)"""
    texto_norm = normalizar(texto)

    # Por número
    numeros = re.findall(r'\b(\d{1,2})\b', texto.strip())
    for n in numeros:
        num = int(n)
        if num in NUMERO_CAMPO_0430:
            clave = NUMERO_CAMPO_0430[num]
            doc = obtener_doc(clave, reporte)
            return clave, doc.get("linaje") if doc else None

    # Por alias
    for alias, clave in ALIAS_0430.items():
        if normalizar(alias) in texto_norm:
            doc = obtener_doc(clave, reporte)
            return clave, doc.get("linaje") if doc else None

    # Por clave directa
    for clave in NUMERO_CAMPO_0430.values():
        if clave.lower() in texto_norm:
            doc = obtener_doc(clave, reporte)
            return clave, doc.get("linaje") if doc else None

    return None, None


def parsear_linaje(campo, linaje_texto, numero=None, reporte="0430"):
    """Obtiene los datos estructurados de MongoDB para la tabla"""
    doc = obtener_doc(campo, reporte) if campo else None
    if not doc:
        return None

    return {
        "campo":         doc.get("clave", campo),
        "numero":        doc.get("numero", numero or ""),
        "origen":        doc.get("origen", ""),
        "hoja_excel":    doc.get("hoja_excel", "—"),
        "columna_excel": doc.get("columna_excel", "—"),
        "tipo":          doc.get("tipo", ""),
        "obligatorio":   doc.get("obligatorio", "—"),
        "formato":       doc.get("formato", "—"),
        "catalogo":      doc.get("catalogo", "—"),
        "condiciones":   doc.get("condiciones", "—"),
        "relacionados":  doc.get("relacionados", []),
    }