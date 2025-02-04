def calcular_digito_verificador(clave_acceso):
    # Inversión de la clave de acceso
    invertido = clave_acceso[::-1]
    
    # Pesos según el SRI
    pesos = [2, 3, 4, 5, 6, 7] * 7
    
    # Calcular el producto de cada dígito por su peso
    suma = sum(int(d) * p for d, p in zip(invertido, pesos))
    
    # Calcular el dígito verificador (módulo 11)
    modulo = 11 - suma % 11
    if modulo == 11:
        return 0
    elif modulo == 10:
        return 1
    else:
        return modulo