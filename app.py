import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página
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
    df['OPCION'] = df.apply(lambda x: f"{x['DESCRIPCION']} (Lab: {x['LABORATORIO']})", axis=1)
    return df

# --- INTERFAZ GRÁFICA ---
st.title("💊 Simulador de Precios de Portafolio vs Farmatodo")

# --- FIRMA DEL DESARROLLADOR ---
st.markdown("#### Desarrollado por: **Econ. Pedro Abreu**")
st.caption("📊 *Consultor de Implementación y Estrategia basada en Datos*")
st.markdown("---")

st.markdown("Sube tu lista, selecciona **múltiples fármacos**, ajusta sus cantidades y descubre el impacto total en tu rentabilidad.")

# 1. Subida del archivo
archivo_subido = st.file_uploader("Sube tu archivo CSV de la lista de precios", type=["csv"])

if archivo_subido is not None:
    df = procesar_csv(archivo_subido)
    
    # Filtrar solo los que tienen datos válidos (que tengan costo y precio farmatodo)
    df_validos = df.dropna(subset=['COSTO_MINIMO', 'FARMATODO']).copy()
    
    # 2. Buscador Múltiple y Filtros
    st.subheader("🛒 Arma tu pedido (Selecciona hasta 10 medicamentos)")
    
    # --- NUEVO: CASILLA DE FILTRO INTELIGENTE ---
    filtrar_rentables = st.checkbox(
        "🛡️ Ocultar productos en pérdida absoluta (Mostrar solo donde mi costo es menor al de Farmatodo)", 
        value=False, 
        help="Si marcas esta casilla, el buscador solo mostrará medicamentos con los que matemáticamente es posible competir."
    )
    
    if filtrar_rentables:
        # Filtra el dataframe dejando solo donde el costo es estrictamente menor al precio del competidor
        df_validos = df_validos[df_validos['COSTO_MINIMO'] < df_validos['FARMATODO']]
        if df_validos.empty:
            st.warning("⚠️ Ningún producto cumple con esta condición. Farmatodo es más barato que tus costos en todo.")
    
    opciones_validas = df_validos['OPCION'].tolist()
    
    seleccionados = st.multiselect(
        "Busca y selecciona los fármacos:", 
        opciones_validas, 
        max_selections=10,
        help="Puedes escribir para buscar y seleccionar varios de la lista."
    )
    
    if seleccionados:
        st.markdown("### ⚙️ Configura tu pedido")
        st.info("💡 **Tip:** Haz doble clic en las columnas de **Cantidad** y **Margen (%)** para editarlas a tu gusto.")
        
        df_sel = df_validos[df_validos['OPCION'].isin(seleccionados)].copy()
        
        tabla_edicion = pd.DataFrame({
            'Medicamento': df_sel['DESCRIPCION'].values,
            'Mejor Proveedor': df_sel['MEJOR_PROVEEDOR'].values,
            'Costo Unit. ($)': df_sel['COSTO_MINIMO'].values,
            'Precio Farmatodo ($)': df_sel['FARMATODO'].values,
            'Cantidad': [30] * len(df_sel),
            'Margen Deseado (%)': [30.0] * len(df_sel)
        })
        
        df_editado = st.data_editor(
            tabla_edicion,
            disabled=['Medicamento', 'Mejor Proveedor', 'Costo Unit. ($)', 'Precio Farmatodo ($)'],
            hide_index=True,
            use_container_width=True
        )
        
        # Botón de calcular
        if st.button("🚀 Calcular Estrategia Global", type="primary"):
            
            inversion_total = 0
            beneficio_total_ideal = 0
            beneficio_total_competidor = 0
            ingreso_total_competidor = 0
            
            resultados_detallados = []
            alertas_rojas = []
            
            for idx, row in df_editado.iterrows():
                costo_u = row['Costo Unit. ($)']
                precio_f = row['Precio Farmatodo ($)']
                cantidad = row['Cantidad']
                margen_pct = row['Margen Deseado (%)'] / 100
                
                costo_total_prod = costo_u * cantidad
                precio_ideal_u = costo_u / (1 - margen_pct)
                beneficio_ideal_prod = (precio_ideal_u * cantidad) - costo_total_prod
                
                beneficio_farma_prod = (precio_f * cantidad) - costo_total_prod
                ingreso_farma_prod = precio_f * cantidad
                
                inversion_total += costo_total_prod
                beneficio_total_ideal += beneficio_ideal_prod
                beneficio_total_competidor += beneficio_farma_prod
                ingreso_total_competidor += ingreso_farma_prod
                
                estado = "✅ Ok"
                if precio_f <= costo_u:
                    estado = "🚨 PÉRDIDA"
                    alertas_rojas.append(row['Medicamento'])
                elif beneficio_farma_prod < beneficio_ideal_prod:
                    estado = "⚠️ Margen Reducido"
                else:
                    estado = "🎉 Mayor Ganancia"
                
                resultados_detallados.append({
                    'Medicamento': row['Medicamento'],
                    'Tu Precio Sugerido': f"${precio_ideal_u:.2f}",
                    'Tu Beneficio Ideal': f"${beneficio_ideal_prod:.2f}",
                    'Beneficio vs Farmatodo': f"${beneficio_farma_prod:.2f}",
                    'Estado': estado
                })
            
            # --- MOSTRAR RESULTADOS GLOBALES ---
            st.divider()
            st.subheader("📊 RESUMEN GLOBAL DEL PEDIDO")
            
            diferencia_global = beneficio_total_competidor - beneficio_total_ideal
            margen_real_global = (beneficio_total_competidor / ingreso_total_competidor) * 100 if ingreso_total_competidor > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Inversión Total (Costo)", f"${inversion_total:.2f}")
            k2.metric("Beneficio Ideal Esperado", f"${beneficio_total_ideal:.2f}")
            
            if beneficio_total_competidor < 0:
                k3.metric("Beneficio Real (vs Farmatodo)", f"${beneficio_total_competidor:.2f}", "PÉRDIDA", delta_color="inverse")
            else:
                k3.metric("Beneficio Real (vs Farmatodo)", f"${beneficio_total_competidor:.2f}", f"{margen_real_global:.1f}% Margen Global")
            
            if diferencia_global < 0:
                k4.metric("Dinero dejado en la mesa", f"${diferencia_global:.2f}", "Si igualas precio", delta_color="inverse")
            else:
                k4.metric("Ganancia Extra", f"+${diferencia_global:.2f}", "Farmatodo es más caro", delta_color="normal")
            
            if alertas_rojas:
                st.error(f"**🚨 ALERTA ROJA:** Los siguientes productos te generarán **pérdida de dinero** si igualas a Farmatodo porque venden por debajo de tu costo: {', '.join(alertas_rojas)}")
            elif diferencia_global < 0:
                st.warning(f"⚠️ **Conclusión Estratégica:** Si decides competir en precio igualando a Farmatodo en todo este pedido, dejarás de ganar **${abs(diferencia_global):.2f}**. Tu margen global bajará a **{margen_real_global:.1f}%**.")
            else:
                st.success("🎉 **¡Excelente!** En el balance global de este pedido, ganas más dinero que con tu escenario ideal si igualas los precios de Farmatodo.")

            st.markdown("### 🔍 Detalle por Fármaco")
            df_resultados = pd.DataFrame(resultados_detallados)
            st.dataframe(df_resultados, hide_index=True, use_container_width=True)
