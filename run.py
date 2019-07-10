# Run a test server.
# from app import app
#
# import sys
# if sys.version_info.major < 3:
#     reload(sys)
#
# app.run(host='0.0.0.0', port=8080, debug=True)


from app import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8080)
