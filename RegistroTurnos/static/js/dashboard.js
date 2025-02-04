// Alternar la visibilidad de la barra lateral en pantallas grandes
$('#toggle-sidebar').on('click', function () {
    $('#sidebar').toggleClass('collapsed');

    // Ajustar el margen izquierdo del contenido
    if ($('#sidebar').hasClass('collapsed')) {
        $('#content').css('margin-left', '0');
    } else {
        $('#content').css('margin-left', '250px'); // Debe coincidir con el ancho inicial del sidebar
    }
});

// AJAX para enviar el formulario de inicio de turno sin recargar la página
$('#form-inicio-turno').on('submit', function (event) {
    event.preventDefault();
    const formData = new FormData(this);
    const dashboardUrl = $(this).data('dashboard-url');

    $.ajax({
        url: dashboardUrl, // URL obtenida del data attribute
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        success: function (response) {
            if (response.success) {
                window.location.href = `/ventas/inicio_turno/${response.turno_id}/`;
            } else {
                alert(response.message || 'Error al iniciar el turno.');
                console.error('Traceback:', response.traceback);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error:', error);
            console.log('Status:', status);
            console.log('XHR Response:', xhr.responseText);
            alert('Ocurrió un error al procesar la solicitud.');
        }
    });
});

