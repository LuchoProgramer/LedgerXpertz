// Obtener el token CSRF
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Comprueba si este es el cookie que buscamos
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

// Configurar AJAX para incluir el token CSRF en las solicitudes
$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!/^GET|HEAD|OPTIONS|TRACE$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        }
    }
});

$(document).ready(function () {
    // Envío del formulario de nuevo cliente
    $('#nuevo-cliente-form').submit(function (event) {
        event.preventDefault();
        var formData = $(this).serialize();

        console.log("Datos enviados al servidor:", formData);

        $.ajax({
            url: crearClienteURL, // Asegúrate de definir esta variable en tu plantilla
            type: 'POST',
            data: formData,
            success: function (response) {
                if (response.success) {
                    // Cerrar el modal
                    $('#nuevoClienteModal').modal('hide');
                    // Limpiar el formulario
                    $('#nuevo-cliente-form')[0].reset();
                    // Limpiar mensajes anteriores
                    $('#modal-mensaje').html('');
                    // Actualizar el select de clientes
                    $('#cliente').append(`<option value="${response.cliente_id}" selected>${response.razon_social} - ${response.identificacion}</option>`);
                    // Mostrar mensaje de éxito en el formulario principal
                    mostrarMensaje('Cliente creado exitosamente.', 'success');
                } else {
                    // Mostrar errores en el modal
                    mostrarErroresModal(response.errors);
                }
            },
            error: function (xhr, status, error) {
                mostrarErroresModal({ '__all__': ['Ocurrió un error al crear el cliente.'] });
            }
        });
    });

    function mostrarErroresModal(errors) {
        var html = '<div class="alert alert-danger">';
        $.each(errors, function (field, messages) {
            html += '<p><strong>' + field + ':</strong> ' + messages.join('<br>') + '</p>';
        });
        html += '</div>';
        $('#modal-mensaje').html(html);
    }

    // Agregar otro método de pago
    $('#add-payment-method').click(function () {
        var paymentMethodHtml = `
            <div class="payment-method row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Método de Pago:</label>
                    <select name="metodos_pago[]" class="form-select metodos_pago">
                        <option value="01">Efectivo</option>
                        <option value="16">Tarjeta de Débito</option>
                        <option value="19">Tarjeta de Crédito</option>
                        <option value="20">Transferencia</option>
                        <option value="17">Dinero Electrónico</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Monto:</label>
                    <input type="number" name="montos_pago[]" class="form-control montos_pago" step="0.01" min="0" required>
                </div>
            </div>
        `;
        $('#payment-methods-container').append(paymentMethodHtml);
        actualizarSaldoRestante();
    });

    // Actualizar saldo restante al cambiar los montos de pago
    $(document).on('input', '.montos_pago', function () {
        actualizarSaldoRestante();
    });

    function actualizarSaldoRestante() {
        var totalFactura = parseFloat($('#total_factura').val().replace(',', '.')) || 0;
        var totalPagado = 0;

        $('.montos_pago').each(function () {
            var monto = parseFloat($(this).val().replace(',', '.')) || 0;
            totalPagado += monto;
        });

        // Convertir a centavos para evitar problemas de precisión
        var totalFacturaCents = Math.round(totalFactura * 100);
        var totalPagadoCents = Math.round(totalPagado * 100);

        var saldoRestanteCents = totalFacturaCents - totalPagadoCents;
        var saldoRestante = saldoRestanteCents / 100;

        // Ajustar pequeños errores de precisión
        if (Math.abs(saldoRestante) < 0.01) {
            saldoRestante = 0;
        }

        $('#saldo_restante').val(saldoRestante.toFixed(2));
    }



    // Manejar el envío del formulario vía AJAX
    $('#factura-form').submit(function (event) {
        event.preventDefault(); // Prevenir el envío normal del formulario

        // Validar que el saldo restante sea cero
        var saldoRestante = parseFloat($('#saldo_restante').val());
        if (Math.abs(saldoRestante) > 0.01) {
            mostrarMensaje('Debes completar el total de la factura con los métodos de pago.', 'danger');
            return;
        }

        // Crear objeto FormData para enviar los datos
        var formData = new FormData(this);

        $.ajax({
            url: generarFacturaURL, // Asegúrate de definir esta variable en tu plantilla
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                if (response.success) {
                    // Mostrar mensaje de éxito
                    mostrarMensaje('Factura generada exitosamente.', 'success');
                    // Redirigir o actualizar la interfaz según sea necesario
                    window.location.href = response.redirect_url;
                } else {
                    mostrarMensaje(response.error, 'danger');
                }
            },
            error: function (xhr, status, error) {
                mostrarMensaje('Ocurrió un error al generar la factura.', 'danger');
            }
        });
    });

    function mostrarMensaje(mensaje, tipo) {
        var html = `
            <div class="alert alert-${tipo} alert-dismissible fade show" role="alert">
                ${mensaje}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        $('#mensaje').html(html);
    }
});