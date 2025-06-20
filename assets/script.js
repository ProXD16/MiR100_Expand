document.addEventListener('DOMContentLoaded', function() {
    var joystickContainer = document.getElementById('joystick');
    if (joystickContainer && window.nipplejs) {
        var joystick = nipplejs.create({
            zone: joystickContainer,
            mode: 'static',
            position: { left: '50%', top: '50%' },
            color: 'blue'
        });
        joystick.on('move', function(evt, data) {
            console.log(data); // Xử lý dữ liệu joystick
            // Có thể gửi dữ liệu qua WebSocket hoặc lưu vào một biến toàn cục
        });
        joystick.on('end', function(evt) {
            console.log('Joystick released');
        });
    }
});