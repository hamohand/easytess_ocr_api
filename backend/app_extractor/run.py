import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8083))
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=port)
