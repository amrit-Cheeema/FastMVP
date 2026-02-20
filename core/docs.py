from fastapi.responses import HTMLResponse

def custom_docs(self):
    @self.app.get("/api", include_in_schema=False)
    async def customDocs():
        return HTMLResponse(f"""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{"title"} • API Documentation</title>

            <!-- Stoplight Elements -->
            <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">

            <!-- Google Font -->
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

            <style>
                :root {{
                    --primary-color: #6366f1;
                    --background-dark: #0f172a;
                    --background-light: #f8fafc;
                }}

                body {{
                    margin: 0;
                    font-family: 'Inter', sans-serif;
                    background: var(--background-light);
                }}

                header {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 14px 24px;
                    background: linear-gradient(90deg, #6366f1, #8b5cf6);
                    color: white;
                    font-weight: 600;
                    font-size: 18px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}

                header span {{
                    opacity: 0.85;
                    font-weight: 400;
                    font-size: 14px;
                }}

                .container {{
                    height: calc(100vh - 60px);
                }}

                elements-api {{
                    height: 100%;
                }}
            </style>
        </head>
        <body>

            <header>
                <div>
                    🚀 {"title"}
                    <span>API Documentation</span>
                </div>
                <div>
                    v1.0
                </div>
            </header>

            <div class="container">
                <elements-api 
                    apiDescriptionUrl="{self.app.openapi_url}" 
                    router="hash"
                    layout="sidebar"
                    tryItCredentialsPolicy="include"
                    hideSchemas="false"
                />
            </div>

        </body>
        </html>
        """)
