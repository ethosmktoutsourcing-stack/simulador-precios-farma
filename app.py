import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página (Pestaña del navegador)
st.set_page_config(page_title="Estrategia de Precios Farma", page_icon="💊", layout="wide")

def limpiar_precio(valor):
    if pd.isna(valor) or str(valor).strip() == '': return np.nan
    valor_limpio = str(valor).replace('$', '').replace(' ', '').replace(',', '.')
    try:
        return float(valor_limpio)
    except ValueError:
        return np.nan

@st.cache_data
def procesar_csv(archivo):
    # Leemos el archivo subido
    df = pd.read_csv(archivo, skiprows=2)
    df.columns = ['Vacio', 'DESCRIPCION', 'LABORATORIO', 'FARMATODO', 'COBECA', 'NENA']
    df = df.drop(columns=['Vacio'])
    
    df['FARMATODO'] = df['FARMATODO'].apply(limpiar_precio)
    df['COBECA'] = df['COBECA'].apply(limpiar_precio)
    df['NENA'] = df['NENA'].apply(limpiar_precio)
    
    df['COSTO_MINIMO'] = df[['COBECA', 'NENA']].min(axis=1)
    
    def elegir_proveedor(row):
        if pd.isna(row['COSTO_MINIMO']): return "Sin precios"
        if row['COSTO_MINIMO'] == row['NENA'] and row['COSTO_MINIMO'] == row['COBECA']: return "Ambos igual"
        if row['COSTO_MINIMO'] == row['NENA']: return "NENA"
        return "COBECA"
        
    df['MEJOR_PROVEEDOR'] = df.apply(elegir_proveedor, axis=1)
    return df

# --- INTERFAZ GRÁFICA ---
st.title("💊 Simulador de Precios vs Farmatodo")

# --- FIRMA DEL DESARROLLADOR ---
st.markdown("#### Desarrollado por: **Econ. Pedro Abreu**")
st.caption("📊 *Consultor de Implementación y Estrategia basada en Datos*")
st.markdown("---") # Línea divisoria elegante

st.markdown("Sube tu lista de precios, busca el fármaco y calcula tu rentabilidad al instante.")

# 1. Subida del archivo
archivo_subido = st.file_uploader("Sube tu archivo CSV de la lista de precios", type=["csv"])

if archivo_subido is not None:
    df = procesar_csv(archivo_subido)
    
    # 2. Buscador integrado
    st.subheader("🔍 Buscar Medicamento")
    busqueda = st.text_input("Escribe el nombre del medicamento (Ej. Losartan, Amlodipina):").upper()
    
    if busqueda:
        resultados = df[df['DESCRIPCION'].str.contains(busqueda, na=False)]
        
        if resultados.empty:
            st.warning("No se encontró ningún medicamento con ese nombre.")
        else:
            # Crear una lista de opciones para el usuario
            opciones = resultados.apply(lambda x: f"{x['DESCRIPCION']} (Lab: {x['LABORATORIO']})", axis=1).tolist()
            seleccion = st.selectbox("Selecciona el medicamento exacto:", opciones)
            
            # Obtener los datos del medicamento seleccionado
            indice_seleccionado = opciones.index(seleccion)
            medicamento = resultados.iloc[indice_seleccionado]
            
            if pd.isna(medicamento['COSTO_MINIMO']) or pd.isna(medicamento['FARMATODO']):
                st.error("⚠️ Este medicamento no tiene los precios completos en el sistema para comparar.")
            else:
                # 3. Mostrar Datos Base
                st.info(f"**Mejor Proveedor:** {medicamento['MEJOR_PROVEEDOR']} | **Costo Unitario:** ${medicamento['COSTO_MINIMO']:.2f} | **Precio Farmatodo:** ${medicamento['FARMATODO']:.2f}")
                
                # 4. Inputs del usuario (Columnas)
                col1, col2 = st.columns(2)
                with col1:
                    cantidad = st.number_input("📦 Cantidad estimada a vender:", min_value=1, value=30)
                with col2:
                    margen = st.number_input("📈 Margen de ganancia deseado (%):", min_value=1.0, value=30.0) / 100
                
                # Botón de calcular
                if st.button("Calcular Estrategia", type="primary"):
                    costo_u = medicamento['COSTO_MINIMO']
                    precio_f = medicamento['FARMATODO']
                    
                    # Cálculos
                    precio_ideal = costo_u / (1 - margen)
                    costo_total = costo_u * cantidad
                    beneficio_ideal = (precio_ideal * cantidad) - costo_total
                    
                    beneficio_competidor = (precio_f * cantidad) - costo_total
                    margen_competidor_pct = (beneficio_competidor / (precio_f * cantidad)) * 100 if (precio_f * cantidad) > 0 else 0
                    
                    # 5. Mostrar Resultados en Tarjetas Visuales
                    st.divider()
                    st.subheader("📊 Resultados de la Comparación")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### 🟢 Tu Escenario Ideal")
                        st.metric("Precio Sugerido", f"${precio_ideal:.2f}")
                        st.metric("Beneficio Total Esperado", f"${beneficio_ideal:.2f}")
                        
                    with c2:
                        st.markdown("### 🔴 Igualando a Farmatodo")
                        st.metric("Precio Farmatodo", f"${precio_f:.2f}")
                        if beneficio_competidor < 0:
                            st.error(f"Beneficio Total: ${beneficio_competidor:.2f} (PÉRDIDA)")
                        else:
                            st.metric("Beneficio Total", f"${beneficio_competidor:.2f}")
                        st.metric("Margen Real", f"{margen_competidor_pct:.2f}%")
                    
                    # 6. Análisis de Impacto
                    st.divider()
                    st.subheader("⚖️ Conclusión de Impacto")
                    
                    if precio_f < precio_ideal:
                        if precio_f <= costo_u:
                            st.error("🚨 **ALERTA ROJA:** Farmatodo vende más barato que el costo de tu proveedor. No compitas en precio aquí.")
                        else:
                            perdida_dinero = beneficio_ideal - beneficio_competidor
                            caida_pct = (perdida_dinero / beneficio_ideal) * 100
                            st.warning(f"⚠️ Al igualar el precio, tu beneficio cae un **{caida_pct:.1f}%**.")
                            st.warning(f"💸 Estás dejando de ganar **${perdida_dinero:.2f}** en esta venta.")
                    elif precio_f > precio_ideal:
                        ganancia_extra = beneficio_competidor - beneficio_ideal
                        st.success(f"🎉 **¡Oportunidad!** Farmatodo es más caro. Si igualas su precio ganarás **${ganancia_extra:.2f}** extra.")
                    else:
                        st.info("Tu precio ideal es exactamente igual al de Farmatodo.")