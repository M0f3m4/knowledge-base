COLUMNAS = {
    "0430": {
        "1":  "PERIODO",
        "2":  "CLAVE DE LA INSTITUCIÓN",
        "3":  "REPORTE",
        "4":  "IDENTIFICADOR DEL ACREDITADO ASIGNADO POR LA INSTITUCIÓN",
        "5":  "NOMBRE DEL ACREDITADO",
        "6":  "RFC DEL ACREDITADO",
        "7":  "CURP DEL ACREDITADO",
        "8":  "LOCALIDAD DEL DOMICILIO DEL ACREDITADO",
        "9":  "MUNICIPIO DEL DOMICILIO DEL ACREDITADO",
        "10": "ESTADO DEL DOMICILIO DEL ACREDITADO",
        "11": "NACIONALIDAD DEL ACREDITADO",
        "12": "ACTIVIDAD ECONÓMICA DEL ACREDITADO",
        "13": "GRUPO DE RIESGO",
        "14": "ACREDITADO RELACIONADO",
        "15": "TIPO DE CARTERA",
        "16": "TIPO DE ANEXO",
        "17": "NÚMERO DE CONSULTA REALIZADA A LA SOCIEDAD DE INFORMACIÓN CREDITICIA",
        "18": "CLAVE LEI LEGAL ENTITY IDENTIFIER",
        "19": "IDENTIFICADOR DEL CRÉDITO ASIGNADO POR LA INSTITUCIÓN",
        "20": "IDENTIFICADOR DEL CRÉDITO ASIGNADO METODOLOGÍA CNBV",
        "21": "IDENTIFICADOR CRÉDITO LÍNEA GRUPAL ASIGNADO METODOLOGÍA CNBV",
        "22": "DESTINO DEL CRÉDITO",
        "23": "MONTO DE LA LÍNEA DE CRÉDITO AUTORIZADO VALORIZADO EN PESOS",
        "24": "MONTO DE LA LÍNEA DE CRÉDITO AUTORIZADO EN LA MONEDA DE ORIGEN",
        "25": "FECHA DE OTORGAMIENTO DE LA LÍNEA DE CRÉDITO",
        "26": "FECHA DE VENCIMIENTO DE LA LÍNEA DE CRÉDITO",
        "27": "FECHA MÁXIMA PARA DISPONER DE LOS RECURSOS",
        "28": "FORMA DE LA DISPOSICIÓN",
        "29": "LÍNEA DE CRÉDITO REVOCABLE O IRREVOCABLE",
        "30": "PRELACIÓN DE PAGO CRÉDITO PREFERENTE O SUBORDINADO",
        "31": "PORCENTAJE DE PARTICIPACIONES FEDERALES COMPROMETIDAS COMO FUENTE DE PAGO DEL CRÉDITO",
        "32": "CLAVE DE LA INSTITUCIÓN O AGENCIA DEL EXTERIOR OTORGANTE DE LOS RECURSOS",
        "33": "TIPO DE ALTA DEL CRÉDITO",
        "34": "MONEDA DE LA LÍNEA DE CRÉDITO",
        "35": "TIPO DE TASA DE INTERÉS DE LA LÍNEA DE CRÉDITO",
        "36": "DIFERENCIAL SOBRE TASA DE REFERENCIA DE LA LÍNEA DE CRÉDITO",
        "37": "OPERACIÓN DE DIFERENCIAL SOBRE TASA DE REFERENCIA ADITIVA O FACTOR DE LA LÍNEA DE CRÉDITO",
        "38": "FRECUENCIA DE REVISIÓN DE LA TASA DE LA LÍNEA DE CRÉDITO",
        "39": "PERIODICIDAD PAGOS DE CAPITAL",
        "40": "PERIODICIDAD PAGOS DE INTERESES",
        "41": "NÚMERO DE MESES DE GRACIA PARA AMORTIZAR CAPITAL",
        "42": "NÚMERO DE MESES DE GRACIA PARA PAGO DE INTERESES",
        "43": "COMISIÓN DE APERTURA DEL CRÉDITO TASA",
        "44": "COMISIÓN DE APERTURA DEL CRÉDITO MONTO",
        "45": "COMISIÓN POR DISPOSICIÓN DEL CRÉDITO TASA",
        "46": "COMISIÓN POR DISPOSICIÓN DEL CRÉDITO MONTO",
        "47": "COSTO ANUAL TOTAL AL MOMENTO DEL OTORGAMIENTO DE LA LÍNEA DE CRÉDITO CALCULADO POR LA INSTITUCIÓN CON SEGUROS OBLIGATORIOS CAT",
        "48": "MONTO DEL CRÉDITO SIMPLE O MONTO AUTORIZADO DE LA LÍNEA DE CRÉDITO SIN INCLUIR ACCESORIOS FINANCIEROS",
        "49": "MONTO DE LAS PRIMAS ANUALES DE TODOS LOS SEGUROS OBLIGATORIOS QUE LA INSTITUCIÓN COBRA AL ACREDITADO",
        "50": "LOCALIDAD EN DONDE SE DESTINARÁ EL CRÉDITO",
        "51": "MUNICIPIO EN DONDE SE DESTINARÁ EL CRÉDITO",
        "52": "ESTADO EN DONDE SE DESTINARÁ EL CRÉDITO",
        "53": "ACTIVIDAD ECONÓMICA A LA QUE SE DESTINARÁ EL CRÉDITO",
    }
}

def resolver_campo(argumento):
    """
    Si el argumento es un número con reporte, resuelve el nombre del campo.
    Ejemplos:
      "9 0430"    → ("MUNICIPIO DEL DOMICILIO DEL ACREDITADO", "0430")
      "RFC 0430"  → ("RFC", "0430")
      "RFC"       → ("RFC", None)
    """
    partes = argumento.strip().split()

    # Detectar si hay número de reporte al final
    if len(partes) > 1 and partes[-1].isdigit() and len(partes[-1]) == 4:
        reporte = partes[-1]
        resto = partes[:-1]
    else:
        reporte = None
        resto = partes

    # Si el campo es solo un número, resolver al nombre
    if len(resto) == 1 and resto[0].isdigit():
        numero = resto[0]
        if reporte and reporte in COLUMNAS:
            nombre = COLUMNAS[reporte].get(numero)
            if nombre:
                print(f"   📌 Columna {numero} → {nombre}")
                return nombre, reporte
        print(f"   ⚠️  Columna {numero} no encontrada en mapa del reporte {reporte}")
        return numero, reporte

    campo = " ".join(resto)
    return campo, reporte