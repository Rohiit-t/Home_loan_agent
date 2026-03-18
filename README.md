# Home Loan Application System 🏠

A complete full-stack intelligent assistant for processing home loan applications with **Streamlit frontend** and LangGraph backend. Features automated document processing, information extraction, risk assessment, and multiple human-in-the-loop interrupt points.

## 🚀 Quick Start - Run the Application

```powershell
# 1. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 2. Set API key (create .env file with OPENROUTER_API_KEY)

# 3. Launch Streamlit app
streamlit run app.py
```

**OR use the convenient launcher:**
```powershell
.\run_app.ps1
```

The application will open at `http://localhost:8501` with a user-friendly interface!

📖 **See [QUICKSTART.md](QUICKSTART.md) for detailed setup guide**

---

## 🌟 Features

### Frontend (Streamlit)
- **Interactive Chat Interface**: Conversational UI with AI assistant
- **Document Upload**: Drag-and-drop file upload with type selection
- **Real-time Status Tracking**: Sidebar showing progress and completion status
- **Dynamic Input Panels**: Context-aware UI adapting to current workflow stage
- **Paused Reason Display**: Clear guidance on what's needed next at each interrupt
- **Action Buttons**: Quick actions for confirmation and navigation

### Backend (LangGraph)
- **Intent Classification**: Automatically determines user intent
- **Multi-modal Input**: Accepts both text and document uploads
- **Document Processing Subgraph**: Modular 3-node pipeline for document verification and extraction
- **Information Extraction**: Extracts personal, financial, and employment details
- **Iterative Data Collection**: Loops until all required information is obtained
- **Risk Assessment**: Calculates LTV, FOIR, and analyzes CIBIL scores
- **Multiple HITL Interrupts**: Four interrupt points for human interaction
  - **Interrupt 1**: Missing documents collection
  - **Interrupt 2**: Missing information collection
  - **Interrupt 3**: Loan details input
  - **Interrupt 4**: Save confirmation
- **Data Persistence**: Dual storage - PostgreSQL database + JSON files in `saved_docs/` folder
- **State Preservation**: Maintains data integrity across multiple loop iterations

## 📊 Complete Workflow

```
┌─────────────────────┐
│   User Message      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Intent Classifier   │
└──────────┬──────────┘
           │
     ┌─────┴─────────────────────┐
     │                           │
     ▼                           ▼
┌─────────────┐         ┌──────────────────┐
│ Irrelevant  │         │ Homeloan Query   │
│  Handler    │         │    Handler       │
└──────┬──────┘         └────────┬─────────┘
       │                         │
       └────────┬────────────────┘
                │
                ▼
         ┌─────────────┐
         │     END     │
         └─────────────┘

     ┌──────────────────────┐
     │  Document_upload     │
     └──────────┬───────────┘
                │
                ▼
     ┌──────────────────────┐
     │ Document Processing  │
     │     SUBGRAPH:        │
     │  ├─ Tampering Check  │
     │  ├─ Classification   │
     │  └─ Data Extraction  │
     └──────────┬───────────┘
                │
                ▼
     ┌──────────────────────┐
     │  State Evaluator     │◄──────┐
     └──────────┬───────────┘       │
                │                   │
         [Missing Data?]            │
                │                   │
                ▼                   │
     ┌──────────────────────┐       │
     │ Text Info Extractor  ├───────┘
     └──────────────────────┘

     ┌──────────────────────┐
     │ Loan Details         │
     │   Collector          │
     └──────────┬───────────┘
                │
                ▼
     ┌──────────────────────┐
     │ Financial Risk       │
     │    Assessment        │
     │  • LTV Check         │
     │  • FOIR Check        │
     │  • CIBIL Check       │
     └──────────┬───────────┘
                │
                ▼
     ┌──────────────────────┐
     │ Save Confirmation    │
     │  (Ask User)          │
     └──────────┬───────────┘
                │
          [User Response]
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
   ┌─────────┐      ┌──────────┐
   │  Save   │      │   Skip   │
   │  Data   │      │   Save   │
   └────┬────┘      └─────┬────┘
        │                 │
        └────────┬────────┘
                 │
                 ▼
         ┌──────────────┐
         │     END      │
         └──────────────┘
```

## 🏗️ Architecture

This project follows **LangGraph industry standards** with a **class-based agent architecture**:

- ✅ All node logic encapsulated in a single `HomeLoanAgent` class
- ✅ Document processing as a reusable subgraph
- ✅ Clean separation of concerns
- ✅ Centralized configuration management
- ✅ Human-in-the-loop interrupts for data approval
- ✅ State preservation across loop iterations
- ✅ Easy to test, maintain, and extend

See [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) for detailed workflow documentation.

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Virtual environment (recommended)
- OpenRouter API key (for LLM)
- PostgreSQL (for database storage)

### Installation Steps

```powershell
# Navigate to project
cd "Home loan-langGraph"

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file with API key
"OPENROUTER_API_KEY=your_api_key_here" | Out-File -FilePath .env -Encoding utf8
```

### Database Configuration

The application saves data to **both PostgreSQL database and JSON files** for redundancy.

**Quick Setup:**

1. **Install PostgreSQL** on your system (if not already installed)

2. **Create Database:**
   ```sql
   CREATE DATABASE homeloan_db;
   ```

3. **Update Configuration:**
   Edit `app/static/config.py` and update the `DATABASE_URL`:
   ```python
   DATABASE_URL = "postgresql://your_username:your_password@localhost:5432/homeloan_db"
   ```

4. **The table is created automatically** on first run

📖 **See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed database configuration and troubleshooting**

### Run the Application

**Option 1: Using the launcher script (Recommended)**
```powershell
.\run_app.ps1
```

**Option 2: Direct Streamlit command**
```powershell
streamlit run app.py
```

**Option 3: Different port**
```powershell
streamlit run app.py --server.port 8502
```

The application will automatically open in your default browser at `http://localhost:8501`

---

## 🎯 Using the Frontend

### Starting a New Application

1. **Click "🚀 Start Application"** button
2. System initializes and asks for first document

### Document Upload Stage

```
⏸️ Action Required: Waiting for documents: aadhaar, pan, itr
```

- Use the **file uploader** on the right panel
- Select document type from dropdown
- Click "Upload Document"
- System automatically extracts data

### Information Input Stage

```
⏸️ Action Required: Waiting for info: personal_info, financial_info
```

- Enter details in the **text area**
- Can use natural language: "My name is John, salary 50000, EMIs 5000"
- Click "Submit Information"

### Loan Details Stage

```
⏸️ Action Required: Waiting for loan details: home_loan_amount, down_payment
```

- Fill in the **loan form** fields:
  - Home Loan Amount
  - Down Payment
  - Tenure (years)
- Click "Submit Loan Details"

### Save Confirmation Stage

```
⏸️ Action Required: Waiting for user confirmation to save data
```

- Review your application
- Click "✅ Yes, Save" to save
- Or "❌ No, Skip" to discard

### Completion

Application saved to `saved_docs/application_{user_id}_{timestamp}.json`

---

## 📘 Documentation

- [QUICKSTART.md](QUICKSTART.md) - Quick setup and test flow
- [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) - Complete Streamlit UI guide
- [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) - Backend workflow details
- [STATE_EVALUATOR_GUIDE.md](STATE_EVALUATOR_GUIDE.md) - State management details
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical summary

---

## 🧪 Programmatic Usage (Advanced)

For developers who want to use the backend directly without the frontend:

### Basic Usage

```python
from langchain_core.messages import HumanMessage
from util.graph import build_graph

# Build the LangGraph application
app = build_graph()

# Initialize state
initial_state = {
    "messages": [HumanMessage(content="I want to apply for a home loan")],
    "intent": None,
    "current_stage": "initial",
    "uploaded_documents": {},
    "personal_info": {},
    "financial_info": {},
    "employment_info": {},
    "all_documents_uploaded": False,
    "paused_reason": None
}

# Run the graph
result = app.invoke(initial_state)

# Access the response
print(result["messages"][-1].content)
```

## 📁 Project Structure

```
Home loan-langGraph/
├── app.py                          # 🎨 Streamlit frontend application
├── run_app.ps1                     # 🚀 Windows launcher script
├── nodes/
│   ├── agent.py                    # HomeLoanAgent class (all 10 nodes)
│   ├── document_processing.py     # Document processing subgraph
│   └── __init__.py
├── util/
│   ├── graph.py                    # Graph builder with interrupt config
│   └── model.py                    # LLM utilities
├── state.py                        # ApplicationState TypedDict schema
├── config.py                       # Configuration (thresholds, requirements)
├── mock_data/                      # Sample documents for testing
│   ├── aadhaar.json
│   ├── pan.json
│   └── itr.json
├── saved_docs/                     # 💾 Saved application JSON files
├── tests/                          # 🧪 Test suite (8 test files)
├── requirements.txt
├── QUICKSTART.md                   # ⚡ Quick start guide  
├── FRONTEND_GUIDE.md              # 📱 Complete frontend documentation
├── WORKFLOW_GUIDE.md              # 🔄 Backend workflow details
├── STATE_EVALUATOR_GUIDE.md       # 📋 State management guide
└── IMPLEMENTATION_SUMMARY.md      # 📊 Technical summary
```

## 🔄 Workflow

```
User Input → Intent Classification
    ↓
    ├─→ Irrelevant → END
    ├─→ Home Loan Query → Answer → END
    ├─→ Document Upload → Process → State Evaluation
    └─→ Text Information → Extract → State Evaluation
                                          ↓
                                    Check Completeness
                                          ↓
                                    Loan Details Collection
                                          ↓
                                    Financial Risk Assessment
                                          ↓
                                        END
```

## 🧪 Example Interactions

### Asking a Query
```python
state = {"messages": [HumanMessage(content="What is the interest rate?")]}
result = app.invoke(state)
# Gets an answer about interest rates and prompts to start application
```

### Providing Information
```python
state = {"messages": [HumanMessage(content="My name is John, I earn $5000 monthly")]}
result = app.invoke(state)
# Extracts name and income information
```

### Loan Details
```python
state = {
    "messages": [HumanMessage(content="I need a loan of $300k with $50k down payment for 20 years")],
    "current_stage": "loan_details_collection"
}
result = app.invoke(state)
# Processes and validates loan details
```

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Document requirements
MANDATORY_DOCS = ["pan", "aadhaar", "salary_slip", "bank_statement", "property_doc"]

# Risk thresholds
LTV_THRESHOLD = 80.0   # Loan to Value (%)
FOIR_THRESHOLD = 50.0  # Fixed Obligation to Income Ratio (%)
MIN_CIBIL = 700        # Minimum credit score
```

## 🔧 Extending the System

### Adding a New Node

1. Add a method to `HomeLoanAgent` class in `nodes/agent.py`:

```python
class HomeLoanAgent:
    # ... existing methods ...
    
    def new_node(self, state: ApplicationState) -> ApplicationState:
        """Your new node logic here."""
        # Process state
        return updated_state
```

2. Register it in `util/graph.py`:

```python
def build_graph():
    agent = HomeLoanAgent()
    graph = StateGraph(ApplicationState)
    
    graph.add_node("new_node", agent.new_node)
    # Add edges...
```

## 📊 State Schema

```python
{
    "user_id": str,
    "messages": List[BaseMessage],
    "intent": str,
    "current_stage": str,
    "uploaded_documents": Dict[str, DocumentMeta],
    "all_documents_uploaded": bool,
    "personal_info": dict,
    "financial_info": dict,
    "employment_info": dict,
    "financial_metrics": dict,
    "paused_reason": str,
    "retry_count": int
}
```

## 🧑‍💻 Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_intent.py
```

### Code Style

This project follows Python best practices:
- Type hints throughout
- Comprehensive docstrings
- Clean code principles
- SOLID design patterns

## 📝 Recent Updates

### Version 3.0 (Current) - Full-Stack Release 🎉
- ✨ **Streamlit Frontend**: Complete interactive UI with chat interface
- 🎯 **Four HITL Interrupt Points**: Missing docs, missing info, loan details, save confirmation
- 📊 **Real-time Status Tracking**: Sidebar with progress indicators
- 🔄 **Iterative Data Collection**: Loops until all requirements met
- 💾 **Data Persistence**: Dual storage - PostgreSQL database + JSON file backup to `saved_docs/`
- 📋 **Paused Reason Display**: Prominent guidance at each interrupt
- 🎨 **Custom UI Components**: Styled boxes for different message types
- 🚀 **PowerShell Launcher**: One-click application startup
- 📚 **Comprehensive Documentation**: 5 detailed guides

### Version 2.0 (Previous)
- ✅ Migrated to class-based architecture
- ✅ Centralized configuration management
- ✅ Document processing subgraph
- ✅ State preservation across loops
- ✅ Better code organization

### Version 1.0 (Legacy)
- Individual function-based nodes
- Basic functionality

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is part of a home loan processing system implementation.

## 🆘 Support

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

**Built with**: LangGraph, LangChain, Streamlit, Python 3.10+  
**Architecture**: Class-based Agent Pattern with Subgraphs  
**Frontend**: Interactive Streamlit UI  
**Status**: Production Ready ✅  

🚀 **Start now**: `streamlit run app.py`
