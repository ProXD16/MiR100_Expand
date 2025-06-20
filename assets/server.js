const express = require('express');
const fs = require('fs');
const app = express();

app.use(express.json());

app.post('/save_drawing', (req, res) => {
    const { image, paths } = req.body;

    // Lưu ảnh
    const base64Data = image.replace(/^data:image\/png;base64,/, '');
    fs.writeFileSync('static/path_img.png', base64Data, 'base64', err => {
        if (err) {
            return res.json({ success: false, message: 'Lỗi lưu ảnh' });
        }
    });

    // Lưu JSON
    fs.writeFileSync('database_json/path_drawn.json', paths, err => {
        if (err) {
            return res.json({ success: false, message: 'Lỗi lưu JSON' });
        }
    });

    res.json({ success: true });
});

app.listen(8000, () => console.log('Server running on port 3000'));