# Router Crack — Priority Checklist

## Credenciales por defecto (Claro Flamingo)

| Usuario | Contraseña común | Probabilidad |
|---------|------------------|--------------|
| admin | password | Alta |
| admin | admin | Media |
| admin | 12345678 | Alta |
| admin | admin123 | Alta |
| root | toor | Media |
| root | root | Baja |
| guest | guest | Baja |

## Puertos Router Comunes

| Puerto | Servicio | SSH? |
|--------|----------|------|
| 22 | SSH | Sí |
| 443 | Web Admin | No (requiere login) |
| 80 | HTTP | No |
| 21 | FTP | No |
| 23 | Telnet | No |

## Diccionarios Recomendados

| Diccionario | Tamaño | Uso recomendado |
|-------------|---------|------------------|
| RockYou | ~14M palabras | WiFi, contraseñas comunes |
| top1k | 1,000 palabras | Contraseñas muy usadas |
| top5000 | 5,000 palabras | Contraseñas populares |
| rockyou-50 | 75K palabras | Versiones populares de RockYou |

## Offline vs Online Cracking

### Offline (John the Ripper / Hashcat)
- **Requiere**: Captura previa de handshake WiFi con `airodump-ng`
- **Velocidad**: Lento en CPU, muy rápido en GPU con Hashcat
- **Uso típico**: WiFi WPA/WEP, hashes AD

### Online (Hydra)
- **Requiere**: Servicio escuchando puerto abierto
- **Velocidad**: Muy rápido (puerto abierto)
- **Uso típico**: SSH, FTP, SMB, HTTP en routers

## Anti-patterns a Evitar

1. **Usar credenciales complejas sin diccionario adecuado** → No se crackeará nunca
2. **Confundir offline con online** → Necesitas handshake para WiFi
3. **No usar GPU para Hashcat** → 100x más lento que en CPU
4. **Diccionario vacío o muy pequeño** → Probabilidad de éxito baja

## Verificación de Herramientas

```bash
# Verificar Hydra
hydra --version

# Verificar RockYou dictionary
wc -l /home/gabo/wordlists/rockyou.txt

# Verificar diccionarios pequeños
ls -lh /home/gabo/wordlists/rockyou*.txt
```
