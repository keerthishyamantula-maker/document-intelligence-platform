const API_BASE_URL = "/api/v1";


// ============================================================
// DOM ELEMENTS
// ============================================================

const uploadForm =
    document.getElementById("uploadForm");

const fileInput =
    document.getElementById("fileInput");

const documentType =
    document.getElementById("documentType");

const processButton =
    document.getElementById("processButton");

const messageBox =
    document.getElementById("messageBox");

const documentsTableBody =
    document.getElementById("documentsTableBody");

const resultPanel =
    document.getElementById("resultPanel");

const resultContent =
    document.getElementById("resultContent");

const refreshButton =
    document.getElementById("refreshButton");


// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function showMessage(
    message,
    type = "info"
) {

    if (!messageBox) {
        return;
    }

    messageBox.textContent =
        message;

    messageBox.className =
        `message ${type}`;

    messageBox.style.display =
        "block";
}


function hideMessage() {

    if (!messageBox) {
        return;
    }

    messageBox.style.display =
        "none";
}


function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


function formatValue(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return `
            <span class="missing-value">
                Missing
            </span>
        `;

    }


    // Handle structured fields such as:
    // { value: null, evidence: null }
    if (
        typeof value === "object" &&
        !Array.isArray(value) &&
        Object.prototype.hasOwnProperty.call(
            value,
            "value"
        )
    ) {

        return formatValue(
            value.value
        );

    }


    if (
        typeof value === "object"
    ) {

        return escapeHtml(
            JSON.stringify(
                value
            )
        );

    }


    return escapeHtml(value);

}


function formatDate(value) {

    if (!value) {
        return "—";
    }


    try {

        return new Date(
            value
        ).toLocaleString();

    } catch {

        return value;

    }

}


function statusClass(status) {

    if (!status) {
        return "status-unknown";
    }


    const normalized =
        String(status)
            .toUpperCase();


    if (
        normalized === "PASS"
    ) {

        return "status-pass";

    }


    if (
        normalized === "FAILED" ||
        normalized === "FAIL"
    ) {

        return "status-failed";

    }


    if (
        normalized ===
        "NOT_APPLICABLE"
    ) {

        return "status-na";

    }


    return "status-unknown";

}


// ============================================================
// DOCUMENT TYPE
// ============================================================

function formatDocumentType(
    value
) {

    const labels = {

        invoice:
            "Invoice",

        balance_sheet:
            "Balance Sheet",

        profit_and_loss:
            "Profit & Loss",

        cash_flow_statement:
            "Cash Flow Statement"

    };


    return (
        labels[value] ||
        value ||
        "Unknown"
    );

}


// ============================================================
// FIELD NAME
// ============================================================

function formatFieldName(
    fieldName
) {

    return String(
        fieldName
    )
        .replace(
            /_/g,
            " "
        )
        .replace(
            /\b\w/g,
            character =>
                character.toUpperCase()
        );

}


// ============================================================
// HEALTH CHECK
// ============================================================

async function checkHealth() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/health`
            );


        if (!response.ok) {

            throw new Error(
                "Backend health check failed."
            );

        }


        const data =
            await response.json();


        console.log(
            "Backend health:",
            data
        );


        return true;

    } catch (error) {

        console.error(
            "Health check error:",
            error
        );


        return false;

    }

}


// ============================================================
// PROCESS DOCUMENT
// ============================================================

async function processDocument(
    event
) {

    if (event) {

        event.preventDefault();

    }


    hideMessage();


    // --------------------------------------------------------
    // Validate document type
    // --------------------------------------------------------

    if (
        !documentType ||
        !documentType.value
    ) {

        showMessage(
            "Please select a document type.",
            "error"
        );

        return;

    }


    // --------------------------------------------------------
    // Validate file
    // --------------------------------------------------------

    if (
        !fileInput ||
        !fileInput.files ||
        !fileInput.files.length
    ) {

        showMessage(
            "Please select a document file.",
            "error"
        );

        return;

    }


    const file =
        fileInput.files[0];


    // --------------------------------------------------------
    // Validate extension
    // --------------------------------------------------------

    const fileName =
        file.name.toLowerCase();


    const allowedExtensions = [
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png"
    ];


    const validExtension =
        allowedExtensions.some(
            extension =>
                fileName.endsWith(
                    extension
                )
        );


    if (!validExtension) {

        showMessage(
            "Unsupported file format. Please upload PDF, JPG, JPEG or PNG.",
            "error"
        );

        return;

    }


    // --------------------------------------------------------
    // FormData
    // --------------------------------------------------------

    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    formData.append(
        "document_type",
        documentType.value
    );


    // --------------------------------------------------------
    // Button
    // --------------------------------------------------------

    if (processButton) {

        processButton.disabled =
            true;

        processButton.textContent =
            "Processing...";

    }


    showMessage(
        `Processing as ${formatDocumentType(
            documentType.value
        )}...`,
        "info"
    );


    // --------------------------------------------------------
    // API CALL
    // --------------------------------------------------------

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/documents/process`,
                {
                    method: "POST",
                    body: formData
                }
            );


        let data;


        try {

            data =
                await response.json();

        } catch {

            throw new Error(
                "The server returned an invalid response."
            );

        }


        if (!response.ok) {

            const serverMessage =
                data?.detail?.message ||
                data?.detail ||
                "Document processing failed.";


            throw new Error(
                serverMessage
            );

        }


        // ----------------------------------------------------
        // Display result immediately
        // ----------------------------------------------------

        displayProcessingResult(
            data.result || data
        );


        // ----------------------------------------------------
        // Refresh dashboard
        // ----------------------------------------------------

        await loadDocuments();


        const result =
            data.result ||
            data;


        const status =
            result.processing_status ||
            result.status ||
            "UNKNOWN";


        if (
            String(status).toUpperCase() ===
            "PASS"
        ) {

            showMessage(
                "Document processed successfully.",
                "success"
            );

        } else {

            showMessage(
                "Document processing completed, but the document did not receive PASS status. Review the result below.",
                "warning"
            );

        }


    } catch (error) {

        console.error(
            "Processing error:",
            error
        );


        showMessage(
            error.message ||
            "Unable to process document.",
            "error"
        );

    } finally {

        if (processButton) {

            processButton.disabled =
                false;

            processButton.textContent =
                "Process Document";

        }

    }

}


// ============================================================
// LOAD PROCESSED DOCUMENTS
// ============================================================

async function loadDocuments() {

    if (!documentsTableBody) {
        return;
    }


    documentsTableBody.innerHTML = `

        <tr>

            <td
                colspan="5"
                class="loading-cell"
            >
                Loading documents...
            </td>

        </tr>

    `;


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/documents`
            );


        if (!response.ok) {

            throw new Error(
                "Unable to retrieve documents."
            );

        }


        const data =
            await response.json();


        renderDocuments(
            data.documents || []
        );


    } catch (error) {

        console.error(
            "Load documents error:",
            error
        );


        documentsTableBody.innerHTML = `

            <tr>

                <td
                    colspan="5"
                    class="error-cell"
                >
                    Unable to load processed documents.
                </td>

            </tr>

        `;

    }

}


// ============================================================
// RENDER DOCUMENT TABLE
// ============================================================

function renderDocuments(
    documents
) {

    if (!documentsTableBody) {
        return;
    }


    if (
        !documents ||
        documents.length === 0
    ) {

        documentsTableBody.innerHTML = `

            <tr>

                <td
                    colspan="5"
                    class="empty-cell"
                >
                    No documents have been processed yet.
                </td>

            </tr>

        `;

        return;

    }


    documentsTableBody.innerHTML =
        documents.map(
            document => {

                const name =
                    document.document_name ||
                    document.file_name ||
                    document.filename ||
                    "Unnamed document";


                const type =
                    document.document_type ||
                    "—";


                const status =
                    document.processing_status ||
                    document.status ||
                    "UNKNOWN";


                const createdAt =
                    document.created_at ||
                    document.processed_at ||
                    document.timestamp ||
                    null;


                const encodedName =
                    encodeURIComponent(
                        document.document_name ||
                        document.file_name ||
                        document.filename ||
                        ""
                    );


                return `

                    <tr>

                        <td>

                            <span
                                class="document-name"
                            >
                                ${escapeHtml(name)}
                            </span>

                        </td>


                        <td>

                            ${escapeHtml(
                                formatDocumentType(
                                    type
                                )
                            )}

                        </td>


                        <td>

                            <span
                                class="status ${statusClass(
                                    status
                                )}"
                            >

                                ${escapeHtml(
                                    status
                                )}

                            </span>

                        </td>


                        <td>

                            ${escapeHtml(
                                formatDate(
                                    createdAt
                                )
                            )}

                        </td>


                        <td>

                            <button
                                type="button"
                                class="view-button"
                                onclick="viewDocument('${encodedName}')"
                            >
                                View Result
                            </button>

                        </td>

                    </tr>

                `;

            }
        )
        .join("");

}


// ============================================================
// VIEW DOCUMENT RESULT
// ============================================================

async function viewDocument(
    encodedDocumentName
) {

    try {

        const documentName =
            decodeURIComponent(
                encodedDocumentName
            );


        if (!documentName) {

            throw new Error(
                "Document name is missing."
            );

        }


        showMessage(
            "Loading document result...",
            "info"
        );


        const response =
            await fetch(
                `${API_BASE_URL}/documents/${encodeURIComponent(
                    documentName
                )}`
            );


        let data;


        try {

            data =
                await response.json();

        } catch {

            throw new Error(
                "The server returned an invalid response."
            );

        }


        if (!response.ok) {

            const serverMessage =
                data?.detail?.message ||
                data?.detail ||
                "Document could not be found.";


            throw new Error(
                serverMessage
            );

        }


        // IMPORTANT:
        // Backend may return either:
        //
        // { ...result... }
        //
        // OR
        //
        // { "result": { ...result... } }

        const result =
            data.result ||
            data;


        displayProcessingResult(
            result
        );


        showMessage(
            "Document result loaded.",
            "success"
        );


    } catch (error) {

        console.error(
            "View document error:",
            error
        );


        showMessage(
            error.message ||
            "Unable to load document.",
            "error"
        );

    }

}


// ============================================================
// MAKE VIEW DOCUMENT AVAILABLE TO HTML
// ============================================================

window.viewDocument =
    viewDocument;


// ============================================================
// DISPLAY PROCESSING RESULT
// ============================================================

function displayProcessingResult(
    result
) {

    if (!resultPanel) {

        console.error(
            "resultPanel was not found."
        );

        return;

    }


    if (!resultContent) {

        console.error(
            "resultContent was not found."
        );

        return;

    }


    // IMPORTANT:
    // resultPanel starts with display:none.

    resultPanel.style.display =
        "block";


    const documentName =
        result.document_name ||
        result.file_name ||
        "Document";


    const type =
        result.document_type ||
        "unknown";


    const status =
        result.processing_status ||
        result.status ||
        "UNKNOWN";


    resultContent.innerHTML = `

        <div class="result-header">

            <div>

                <h3>
                    ${escapeHtml(
                        documentName
                    )}
                </h3>


                <p>

                    Type:

                    <strong>

                        ${escapeHtml(
                            formatDocumentType(
                                type
                            )
                        )}

                    </strong>

                </p>

            </div>


            <span
                class="status ${statusClass(status)}"
            >

                ${escapeHtml(
                    status
                )}

            </span>

        </div>


        ${renderFileValidation(
            result.file_validation
        )}


        ${renderExtractedData(
            result.extracted_data ||
            result.extraction?.data ||
            result.extraction
        )}


        ${renderFinancialValidation(
            result.validation ||
            result.financial_validation
        )}


        ${renderIssues(
            result
        )}


        <details class="raw-json">

            <summary>
                View Raw JSON
            </summary>


            <pre>

${escapeHtml(
    JSON.stringify(
        result,
        null,
        2
    )
)}

            </pre>

        </details>

    `;


    // Scroll to result

    resultPanel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}


// ============================================================
// FILE VALIDATION
// ============================================================

function renderFileValidation(
    validation
) {

    if (!validation) {

        return `

            <section class="result-card">

                <h3>
                    File Validation
                </h3>

                <p>
                    No validation result available.
                </p>

            </section>

        `;

    }


    return `

        <section class="result-card">

            <h3>
                File Validation
            </h3>


            <div class="info-grid">

                ${renderInfoCard(
                    "File Type",
                    validation.file_type
                )}


                ${renderInfoCard(
                    "Is Supported",
                    validation.is_supported
                )}


                ${renderInfoCard(
                    "Is Readable",
                    validation.is_readable
                )}


                ${renderInfoCard(
                    "Page Count",
                    validation.page_count
                )}


                ${renderInfoCard(
                    "Status",
                    validation.status
                )}

            </div>

        </section>

    `;

}


// ============================================================
// EXTRACTED DATA
// ============================================================

function renderExtractedData(
    data
) {

    if (!data) {

        return `

            <section class="result-card">

                <h3>
                    Extracted Data
                </h3>

                <p class="missing-value">
                    No extracted data available.
                </p>

            </section>

        `;

    }


    let html = `

        <section class="result-card">

            <h3>
                Extracted Data
            </h3>

    `;


    // --------------------------------------------------------
    // Fields
    // --------------------------------------------------------

    if (
        data.fields &&
        typeof data.fields === "object" &&
        !Array.isArray(data.fields)
    ) {

        html += `

            <h4>
                Fields
            </h4>

            <div class="key-value-grid">

        `;


        for (
            const [
                key,
                value
            ]
            of Object.entries(
                data.fields
            )
        ) {

            html += `

                <div class="key-value-item">

                    <div class="key">

                        ${escapeHtml(
                            formatFieldName(
                                key
                            )
                        )}

                    </div>


                    <div class="value">

                        ${formatValue(
                            value
                        )}

                    </div>

                </div>

            `;

        }


        html += `

            </div>

        `;

    }


    // --------------------------------------------------------
    // Direct fields
    // --------------------------------------------------------

    const reservedKeys =
        new Set([
            "fields",
            "statement_items",
            "line_items",
            "reporting_periods",
            "evidence",
            "document_type"
        ]);


    const directFields = {};


    for (
        const [
            key,
            value
        ]
        of Object.entries(data)
    ) {

        if (
            !reservedKeys.has(key)
        ) {

            if (
                typeof value !== "object" ||
                value === null
            ) {

                directFields[key] =
                    value;

            }

        }

    }


    if (
        Object.keys(
            directFields
        ).length
    ) {

        html += `

            <h4>
                Extracted Fields
            </h4>

            <div class="key-value-grid">

        `;


        for (
            const [
                key,
                value
            ]
            of Object.entries(
                directFields
            )
        ) {

            html += `

                <div class="key-value-item">

                    <div class="key">

                        ${escapeHtml(
                            formatFieldName(
                                key
                            )
                        )}

                    </div>


                    <div class="value">

                        ${formatValue(
                            value
                        )}

                    </div>

                </div>

            `;

        }


        html += `

            </div>

        `;

    }


    // --------------------------------------------------------
    // Reporting periods
    // --------------------------------------------------------

    if (
        data.reporting_periods
    ) {

        const periods =
            data.reporting_periods?.value ??
            data.reporting_periods;


        html += `

            <h4>
                Reporting Periods
            </h4>

            <div class="key-value-grid">

                <div class="key-value-item">

                    <div class="key">
                        Reporting Periods
                    </div>

                    <div class="value">

                        ${formatValue(
                            Array.isArray(periods)
                                ? periods.join(" | ")
                                : periods
                        )}

                    </div>

                </div>

            </div>

        `;

    }


    // --------------------------------------------------------
    // Statement items
    // --------------------------------------------------------

    if (
        Array.isArray(
            data.statement_items
        ) &&
        data.statement_items.length
    ) {

        html += `

            <h4>
                Financial Statement Items
            </h4>

            <div class="table-wrapper">

                <table class="data-table">

                    <thead>

                        <tr>

                            <th>
                                Item
                            </th>

                            <th>
                                Schedule
                            </th>

                            <th>
                                Values
                            </th>

                            <th>
                                Evidence
                            </th>

                        </tr>

                    </thead>


                    <tbody>

        `;


        for (
            const item
            of data.statement_items
        ) {

            const values =
                Array.isArray(
                    item.values
                )
                    ? item.values
                    : [];


            const valuesHtml =
                values
                    .map(
                        value => `

                            <div>

                                <strong>

                                    ${escapeHtml(
                                        value?.period ||
                                        ""
                                    )}

                                </strong>

                                :

                                ${formatValue(
                                    value?.value
                                )}

                            </div>

                        `
                    )
                    .join("");


            const evidence =
                item.evidence ||
                {};


            const sourceText =
                evidence.source_text ||
                evidence.text ||
                "";


            html += `

                <tr>

                    <td>

                        ${escapeHtml(
                            item.line_item ||
                            item.item ||
                            "—"
                        )}

                    </td>


                    <td>

                        ${escapeHtml(
                            item.schedule ||
                            "—"
                        )}

                    </td>


                    <td>

                        ${valuesHtml || "—"}

                    </td>


                    <td>

                        ${escapeHtml(
                            sourceText ||
                            "—"
                        )}

                        ${
                            evidence.page_number !==
                            undefined &&
                            evidence.page_number !==
                            null
                                ? `
                                    <br>

                                    <small>

                                        Page
                                        ${escapeHtml(
                                            evidence.page_number
                                        )}

                                    </small>
                                `
                                : ""
                        }

                    </td>

                </tr>

            `;

        }


        html += `

                    </tbody>

                </table>

            </div>

        `;

    }


    // --------------------------------------------------------
    // Invoice line items
    // --------------------------------------------------------

    if (
        Array.isArray(
            data.line_items
        ) &&
        data.line_items.length
    ) {

        html += `

            <h4>
                Invoice Line Items
            </h4>

            <div class="table-wrapper">

                <table class="data-table">

                    <thead>

                        <tr>

                            <th>
                                Description
                            </th>

                            <th>
                                Quantity
                            </th>

                            <th>
                                Unit Price
                            </th>

                            <th>
                                Amount
                            </th>

                        </tr>

                    </thead>


                    <tbody>

        `;


        for (
            const item
            of data.line_items
        ) {

            html += `

                <tr>

                    <td>

                        ${escapeHtml(
                            item.description ??
                            "—"
                        )}

                    </td>


                    <td>

                        ${escapeHtml(
                            item.quantity ??
                            "—"
                        )}

                    </td>


                    <td>

                        ${escapeHtml(
                            item.unit_price ??
                            "—"
                        )}

                    </td>


                    <td>

                        ${escapeHtml(
                            item.amount ??
                            item.line_total ??
                            "—"
                        )}

                    </td>

                </tr>

            `;

        }


        html += `

                    </tbody>

                </table>

            </div>

        `;

    }


    html += `

        </section>

    `;


    return html;

}


// ============================================================
// FINANCIAL VALIDATION
// ============================================================

function renderFinancialValidation(
    validation
) {

    if (!validation) {

        return `

            <section class="result-card">

                <h3>
                    Financial Validation
                </h3>

                <p>
                    No financial validation result available.
                </p>

            </section>

        `;

    }


    const overallStatus =
        validation.overall_status ||
        "NOT_APPLICABLE";


    const checks =
        Array.isArray(
            validation.checks
        )
            ? validation.checks
            : [];


    let html = `

        <section class="result-card">

            <h3>
                Financial Validation
            </h3>


            <p>

                <strong>
                    Overall Status:
                </strong>


                <span
                    class="status ${statusClass(
                        overallStatus
                    )}"
                >

                    ${escapeHtml(
                        overallStatus
                    )}

                </span>

            </p>

    `;


    if (!checks.length) {

        html += `

            <p class="missing-value">

                No applicable financial checks
                were available.

            </p>

        `;

    } else {

        html += `

            <div class="table-wrapper">

                <table class="data-table">

                    <thead>

                        <tr>

                            <th>
                                Check
                            </th>

                            <th>
                                Formula
                            </th>

                            <th>
                                Period
                            </th>

                            <th>
                                Calculated
                            </th>

                            <th>
                                Reported
                            </th>

                            <th>
                                Variance
                            </th>

                            <th>
                                Status
                            </th>

                        </tr>

                    </thead>


                    <tbody>

        `;


        for (
            const check
            of checks
        ) {

            html += `

                <tr>

                    <td>

                        ${escapeHtml(
                            check.name ||
                            check.check ||
                            "—"
                        )}

                    </td>


                    <td>

                        ${escapeHtml(
                            check.formula ||
                            "—"
                        )}

                    </td>


                    <td>

                        ${escapeHtml(
                            check.period ||
                            "—"
                        )}

                    </td>


                    <td>

                        ${formatValue(
                            check.calculated_value ??
                            check.calculated
                        )}

                    </td>


                    <td>

                        ${formatValue(
                            check.reported_value ??
                            check.reported
                        )}

                    </td>


                    <td>

                        ${formatValue(
                            check.variance
                        )}

                    </td>


                    <td>

                        <span
                            class="status ${statusClass(
                                check.status
                            )}"
                        >

                            ${escapeHtml(
                                check.status ||
                                "—"
                            )}

                        </span>

                    </td>

                </tr>

            `;

        }


        html += `

                    </tbody>

                </table>

            </div>

        `;

    }


    html += `

        </section>

    `;


    return html;

}


// ============================================================
// ISSUES
// ============================================================

function renderIssues(
    result
) {

    const issues = [];


    if (
        Array.isArray(
            result.issues
        )
    ) {

        issues.push(
            ...result.issues
        );

    }


    if (
        result.financial_validation &&
        Array.isArray(
            result.financial_validation.issues
        )
    ) {

        issues.push(
            ...result.financial_validation.issues
        );

    }


    if (
        result.validation &&
        Array.isArray(
            result.validation.issues
        )
    ) {

        issues.push(
            ...result.validation.issues
        );

    }


    if (!issues.length) {

        return "";

    }


    return `

        <section class="result-card issues">

            <h3>
                Issues
            </h3>


            <ul>

                ${issues
                    .map(
                        issue => `

                            <li>

                                ${escapeHtml(
                                    typeof issue ===
                                    "string"
                                        ? issue
                                        : issue.message ||
                                          String(issue)
                                )}

                            </li>

                        `
                    )
                    .join("")}

            </ul>

        </section>

    `;

}


// ============================================================
// INFO CARD
// ============================================================

function renderInfoCard(
    label,
    value
) {

    return `

        <div class="key-value-item">

            <div class="key">

                ${escapeHtml(
                    label
                )}

            </div>


            <div class="value">

                ${formatValue(
                    value
                )}

            </div>

        </div>

    `;

}


// ============================================================
// EVENT LISTENERS
// ============================================================

if (uploadForm) {

    uploadForm.addEventListener(
        "submit",
        processDocument
    );

}


if (refreshButton) {

    refreshButton.addEventListener(
        "click",
        loadDocuments
    );

}


// ============================================================
// INITIAL PAGE LOAD
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    async function () {

        console.log(
            "Document Intelligence Dashboard loaded."
        );


        const healthy =
            await checkHealth();


        if (!healthy) {

            showMessage(
                "Backend API is not available. Make sure the FastAPI server is running.",
                "error"
            );

        }


        await loadDocuments();

    }
);