import sys
import uvicorn
from mock_factory import create_app

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_mock.py <spec_file.json> [port]")
        print("Example: python run_mock.py petstore.json 8000")
        sys.exit(1)

    spec_path = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    app = create_app(spec_path)

    print(f"\nMock server starting on http://127.0.0.1:{port}")
    print(f"Interactive docs: http://127.0.0.1:{port}/docs\n")

    uvicorn.run(app, host="127.0.0.1", port=port)