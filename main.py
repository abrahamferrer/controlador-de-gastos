from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import datos
import os
from datetime import datetime, date
import decimal

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Genera una clave secreta aleatoria para la sesión

def get_db_connection():
    return mysql.connector.connect(
        host=datos.HOST,
        user=datos.USER,
        password=datos.PASSWORD,
        database=datos.DATABASE,
        port=datos.PORT,
        connection_timeout=600  # Aumenta el timeout a 600 segundos
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.pop('id', None)
    return redirect(url_for('home'))

@app.route("/agregar_movimiento", methods=["POST"])
def agregar_movimiento():
    descripcion = request.form.get("descripcion")
    monto = request.form.get("monto")
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Fecha y hora actual
    tipo = request.form.get("tipo")
    
    # Se asume que el usuario está autenticado y su ID está en la sesión
    usuario_id = session.get("id")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO movimientos (descripcion, monto, fecha, tipo, usuario_id) VALUES (%s, %s, %s, %s, %s)",
        (descripcion, monto, fecha, tipo, usuario_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('inicio'))

@app.route('/inicio')
def inicio():
    if 'id' in session:
        id_usuario = session['id']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calcular totales de ingresos y egresos
        cursor.execute("SELECT SUM(monto) FROM movimientos WHERE usuario_id = %s AND tipo = 'ingreso'", (id_usuario,))
        total_ingresos = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(monto) FROM movimientos WHERE usuario_id = %s AND tipo = 'egreso'", (id_usuario,))
        total_gastos = cursor.fetchone()[0] or 0

        saldo_total = total_ingresos - total_gastos

        # Obtener todos los movimientos para el usuario
        cursor.execute("SELECT id, descripcion, monto, tipo, fecha FROM movimientos WHERE usuario_id = %s", (id_usuario,))
        movimientos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convertir cada campo de cada movimiento a un tipo serializable
        movimientos_serializables = []
        for row in movimientos:
            nuevo_registro = []
            for campo in row:
                if isinstance(campo, bytearray):
                    nuevo_registro.append(campo.decode('utf-8'))
                elif isinstance(campo, decimal.Decimal):
                    nuevo_registro.append(float(campo))
                elif isinstance(campo, (datetime, date)):
                    nuevo_registro.append(campo.strftime('%Y-%m-%d'))
                else:
                    nuevo_registro.append(campo)
            movimientos_serializables.append(nuevo_registro)
            
        return render_template('inicio.html',
                               total_ingresos=total_ingresos,
                               total_gastos=total_gastos,
                               saldo_total=saldo_total,
                               movimientos=movimientos_serializables)
    else:
        return redirect(url_for('login'))
    
@app.route('/perfil')
def perfil():
    if 'id' in session:
        id_usuario = session['id']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, password, id FROM usuarios WHERE id = %s", (id_usuario,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if usuario is not None:
            # Convertir posibles bytes/bytearray a string
            usuario_convertido = []
            for campo in usuario:
                if isinstance(campo, (bytes, bytearray)):
                    usuario_convertido.append(campo.decode('utf-8'))
                else:
                    usuario_convertido.append(campo)
            return render_template('perfil.html', usuario=usuario_convertido)
    return render_template('perfil.html', usuario=None)


@app.route('/registro')
def registro():
    return render_template('registro.html')

@app.route('/analisis')
def analisis():
    if 'id' in session:
        id_usuario = session['id']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, descripcion, monto, tipo, fecha FROM movimientos WHERE usuario_id = %s", (id_usuario,))
        movimientos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        movimientos_serializables = []
        for row in movimientos:
            nuevo_registro = []
            for campo in row:
                if isinstance(campo, bytearray):
                    nuevo_registro.append(campo.decode('utf-8'))
                elif isinstance(campo, decimal.Decimal):
                    nuevo_registro.append(float(campo))
                elif isinstance(campo, (datetime, date)):
                    nuevo_registro.append(campo.strftime('%Y-%m-%d'))
                else:
                    nuevo_registro.append(campo)
            movimientos_serializables.append(nuevo_registro)
        
        # En este ejemplo, dejamos los totales en 0; se pueden calcular similar a /inicio si se requiere.
        total_ingresos = 0
        total_gastos = 0
        saldo_total = 0

        return render_template('analisis.html',
                               total_ingresos=total_ingresos,
                               total_gastos=total_gastos,
                               saldo_total=saldo_total,
                               movimientos=movimientos_serializables)
    else:
        return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/validacion_login', methods=['POST'])
def validacion_login():
    email = request.form.get("email")
    password = request.form.get("password")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = %s AND password = %s", (email, password))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if usuario is not None:
        session['id'] = usuario[0]  # Se asume que el primer campo es el id
        return redirect(url_for('inicio'))
    else:
        return redirect(url_for('login'))

@app.route('/validacion_registro', methods=['POST'])
def validacion_registro():
    name = request.form.get("u_name")
    email = request.form.get("u_email")
    password = request.form.get("u_password")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usuarios (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
    conn.commit()
    cursor.close()
    conn.close()
    
    return render_template('login.html')
    
if __name__ == '__main__':
    app.run(debug=True)
