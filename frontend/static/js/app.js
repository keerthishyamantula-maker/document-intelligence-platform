"use strict";

/*
 * ============================================================
 * DOCUMENT INTELLIGENCE PLATFORM - FRONTEND
 * ============================================================
 *
 * This file handles:
 *   - File upload
 *   - Document type selection
 *   - API processing
 *   - Dashboard document list
 *   - Individual document results
 *   - File validation display
 *   - AI extracted data display
 *   - Financial validation display
 *   - Evidence display
 *   - Raw JSON display
 *
 * Backend:
 *   FastAPI
 *
 * API prefix:
 *   /api/v1
 * ============================================================
 */


// ============================================================
// CONFIGURATION
// ============================================================

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
// GENERAL HELPERS
// ============================================================

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


function safeText(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value).trim();
}


function getDisplayValue(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return null;
    }

    /*
     * Backend may return structured values such as:
     *
     * {
     *     "value": 1234
     * }
     *
     * or:
     *
     * {
     *     "reported_value": 1234
     * }
     */

    if (
        typeof value === "object" &&
        !Array.isArray(value)
    ) {

        if (
            Object.prototype.hasOwnProperty.call(
                value,
                "value"
            )
        ) {
            return getDisplayValue(
                value.value
            );
        }

        if (
            Object.prototype.hasOwnProperty.call(
                value,
                "reported_value"
            )
        ) {
            return getDisplayValue(
                value.reported_value
            );
        }

        if (
            Object.prototype.hasOwnProperty.call(
                value,
                "calculated_value"
            )
        ) {
            return getDisplayValue(
                value.calculated_value
            );
        }
    }

    return value;
}


function formatValue(value) {

    const displayValue =
        getDisplayValue(value);

    if (
        displayValue === null ||
        displayValue === undefined ||
        displayValue === ""
    ) {

        return `
            <span class="missing-value">
                Missing
            </span>
        `;
    }


    if (
        typeof displayValue === "boolean"
    ) {

        return displayValue
            ? "Yes"
            : "No";
    }


    if (
        Array.isArray(displayValue)
    ) {

        return escapeHtml(
            displayValue.join(" | ")
        );
    }


    if (
        typeof displayValue === "object"
    ) {

        return `
            <pre class="inline-json">${escapeHtml(
                JSON.stringify(
                    displayValue,
                    null,
                    2
                )
            )}</pre>
        `;
    }


    return escapeHtml(
        String(displayValue)
    );
}


function formatFieldName(name) {

    if (!name) {
        return "";
    }

    return String(name)
        .replace(/_/g, " ")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/\b\w/g, character =>
            character.toUpperCase()
        );
}


function formatDocumentType(type) {

    if (!type) {
        return "Unknown";
    }

    const normalized =
        String(type)
            .trim()
            .toLowerCase();

    const mapping = {
        invoice: "Invoice",
        balance_sheet: "Balance Sheet",
        "balance sheet": "Balance Sheet",
        profit_and_loss: "Profit & Loss",
        "profit and loss": "Profit & Loss",
        pnl: "Profit & Loss",
        cash_flow: "Cash Flow Statement",
        "cash flow": "Cash Flow Statement",
        "cash flow statement": "Cash Flow Statement"
    };

    return (
        mapping[normalized] ||
        String(type)
    );
}


function statusClass(status) {

    if (!status) {
        return "status-neutral";
    }

    const normalized =
        String(status)
            .trim()
            .toLowerCase();

    if (
        normalized === "pass" ||
        normalized === "passed" ||
        normalized === "success" ||
        normalized === "successful" ||
        normalized === "valid"
    ) {
        return "status-success";
    }

    if (
        normalized === "fail" ||
        normalized === "failed" ||
        normalized === "error" ||
        normalized === "invalid"
    ) {
        return "status-error";
    }

    if (
        normalized === "not_applicable" ||
        normalized === "not applicable" ||
        normalized === "n/a"
    ) {
        return "status-warning";
    }

    return "status-neutral";
}


function formatDate(value) {

    if (!value) {
        return "—";
    }

    try {

        const date =
            new Date(value);

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return escapeHtml(
                String(value)
            );
        }

        return date.toLocaleString();

    } catch (error) {

        return escapeHtml(
            String(value)
        );
    }
}


function formatEvidence(evidence) {

    if (!evidence) {
        return "—";
    }

    if (
        typeof evidence === "string"
    ) {

        if (evidence.length <= 240) {
            return escapeHtml(evidence);
        }

        return `
            <details>
                <summary>
                    View evidence
                </summary>

                <div class="evidence-text">
                    ${escapeHtml(evidence)}
                </div>
            </details>
        `;
    }


    if (
        typeof evidence !== "object"
    ) {
        return escapeHtml(
            String(evidence)
        );
    }


    const sourceText =
        evidence.source_text ||
        evidence.text ||
        evidence.raw_text ||
        evidence.evidence ||
        "";


    const pageNumber =
        evidence.page_number ??
        evidence.page ??
        null;


    if (!sourceText) {

        return escapeHtml(
            JSON.stringify(evidence)
        );
    }


    const pageHtml =
        pageNumber !== null
            ? `
                <br>
                <small>
                    Page ${escapeHtml(pageNumber)}
                </small>
              `
            : "";


    if (
        String(sourceText).length <= 240
    ) {

        return `
            ${escapeHtml(sourceText)}
            ${pageHtml}
        `;
    }


    return `
        <details>

            <summary>
                View evidence
            </summary>

            <div class="evidence-text">
                ${escapeHtml(sourceText)}
            </div>

            ${pageHtml}

        </details>
    `;
}


function normalizeResponseData(response) {

    if (!response) {
        return null;
    }


    if (
        response.data &&
        typeof response.data === "object" &&
        !Array.isArray(response.data)
    ) {

        /*
         * Only unwrap if the outer response looks
         * like a wrapper rather than actual extracted data.
         */

        if (
            response.success !== undefined ||
            response.status !== undefined ||
            response.message !== undefined
        ) {
            return response.data;
        }
    }


    return response;
}


// ============================================================
// MESSAGE DISPLAY
// ============================================================

function showMessage(
    message,
    type = "info"
) {

    if (!messageBox) {
        return;
    }


    messageBox.textContent =
        message || "";


    messageBox.className =
        `message-box ${type}`;


    messageBox.style.display =
        message
            ? "block"
            : "none";
}


function clearMessage() {

    if (!messageBox) {
        return;
    }

    messageBox.textContent = "";

    messageBox.style.display =
        "none";
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
            return false;
        }


        const data =
            await response.json();


        return (
            data.status === "healthy" ||
            data.status === "ok" ||
            data.healthy === true ||
            response.ok
        );

    } catch (error) {

        console.error(
            "Health check failed:",
            error
        );

        return false;
    }
}


// ============================================================
// PROCESS DOCUMENT
// ============================================================

async function processDocument(event) {

    event.preventDefault();

    clearMessage();


    if (!fileInput) {

        showMessage(
            "File input is not available.",
            "error"
        );

        return;
    }


    const file =
        fileInput.files &&
        fileInput.files[0];


    if (!file) {

        showMessage(
            "Please select a PDF, JPG, or PNG file.",
            "error"
        );

        return;
    }


    const selectedType =
        documentType
            ? documentType.value
            : "";


    if (!selectedType) {

        showMessage(
            "Please select a document type.",
            "error"
        );

        return;
    }


    const allowedTypes = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png"
    ];


    const fileName =
        file.name.toLowerCase();


    const validExtension =
        fileName.endsWith(".pdf") ||
        fileName.endsWith(".jpg") ||
        fileName.endsWith(".jpeg") ||
        fileName.endsWith(".png");


    if (
        !allowedTypes.includes(file.type) &&
        !validExtension
    ) {

        showMessage(
            "Unsupported file type. Please upload PDF, JPG, or PNG.",
            "error"
        );

        return;
    }


    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    formData.append(
        "document_type",
        selectedType
    );


    /*
     * Prevent duplicate submissions.
     */

    if (processButton) {

        processButton.disabled =
            true;

        processButton.dataset.originalText =
            processButton.textContent;

        processButton.textContent =
            "Processing...";
    }


    showMessage(
        "Uploading and processing document. Please wait...",
        "info"
    );


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/documents/process`,
                {
                    method: "POST",
                    body: formData
                }
            );


        let result = null;


        try {

            result =
                await response.json();

        } catch (jsonError) {

            throw new Error(
                `Server returned an invalid response (${response.status}).`
            );
        }


        if (!response.ok) {

            const errorMessage =
                result?.detail ||
                result?.message ||
                result?.error ||
                `Processing failed with HTTP ${response.status}.`;

            throw new Error(
                errorMessage
            );
        }


        /*
         * The backend may wrap the actual result
         * inside "result".
         */

        if (
            result &&
            result.result &&
            typeof result.result === "object"
        ) {

            result =
                result.result;
        }


        displayProcessingResult(
            result
        );


        showMessage(
            "Document processed successfully.",
            "success"
        );


        await loadDocuments();


    } catch (error) {

        console.error(
            "Document processing failed:",
            error
        );


        showMessage(
            error.message ||
            "Unable to process the document.",
            "error"
        );


        if (resultContent) {

            resultContent.innerHTML = `
                <section class="result-card">

                    <h3>
                        Processing Error
                    </h3>

                    <p class="missing-value">
                        ${escapeHtml(
                            error.message ||
                            "Unknown processing error."
                        )}
                    </p>

                </section>
            `;
        }


    } finally {

        if (processButton) {

            processButton.disabled =
                false;

            processButton.textContent =
                processButton.dataset.originalText ||
                "Process Document";
        }
    }
}


// ============================================================
// LOAD DOCUMENTS
// ============================================================

async function loadDocuments() {

    if (!documentsTableBody) {
        return;
    }


    try {

        documentsTableBody.innerHTML = `
            <tr>
                <td colspan="6">
                    Loading documents...
                </td>
            </tr>
        `;


        const response =
            await fetch(
                `${API_BASE_URL}/documents`
            );


        if (!response.ok) {

            throw new Error(
                `Unable to load documents (${response.status}).`
            );
        }


        const data =
            await response.json();


        let documents = data;


        if (
            data &&
            Array.isArray(data.documents)
        ) {

            documents =
                data.documents;
        }


        if (
            data &&
            Array.isArray(data.results)
        ) {

            documents =
                data.results;
        }


        if (
            !Array.isArray(documents)
        ) {

            documents = [];
        }


        renderDocuments(
            documents
        );


    } catch (error) {

        console.error(
            "Failed to load documents:",
            error
        );


        documentsTableBody.innerHTML = `
            <tr>
                <td colspan="6">

                    <span class="missing-value">
                        Unable to load documents.
                    </span>

                </td>
            </tr>
        `;
    }
}


// ============================================================
// RENDER DOCUMENT LIST
// ============================================================

function renderDocuments(documents) {

    if (!documentsTableBody) {
        return;
    }


    if (!documents.length) {

        documentsTableBody.innerHTML = `
            <tr>

                <td
                    colspan="6"
                    style="text-align:center;"
                >
                    No documents processed yet.
                </td>

            </tr>
        `;

        return;
    }


    documentsTableBody.innerHTML =
        documents
            .map(document => {

                const name =
                    document.document_name ||
                    document.filename ||
                    document.file_name ||
                    document.name ||
                    "Unknown";


                const type =
                    document.document_type ||
                    document.type ||
                    "Unknown";


                const status =
                    document.status ||
                    document.processing_status ||
                    "Unknown";


                const createdAt =
                    document.created_at ||
                    document.processed_at ||
                    document.created ||
                    null;


                const pageCount =
                    document.page_count ??
                    document.pages ??
                    "—";


                const encodedName =
                    encodeURIComponent(
                        name
                    );


                return `
                    <tr>

                        <td>
                            ${escapeHtml(name)}
                        </td>

                        <td>
                            ${escapeHtml(
                                formatDocumentType(type)
                            )}
                        </td>

                        <td>
                            <span
                                class="status ${statusClass(status)}"
                            >
                                ${escapeHtml(status)}
                            </span>
                        </td>

                        <td>
                            ${escapeHtml(
                                String(pageCount)
                            )}
                        </td>

                        <td>
                            ${formatDate(createdAt)}
                        </td>

                        <td>

                            <button
                                type="button"
                                class="view-button"
                                onclick="viewDocument('${encodedName}')"
                            >
                                View
                            </button>

                        </td>

                    </tr>
                `;

            })
            .join("");
}


// ============================================================
// VIEW SINGLE DOCUMENT
// ============================================================

async function viewDocument(encodedName) {

    clearMessage();


    let documentName;


    try {

        documentName =
            decodeURIComponent(
                encodedName
            );

    } catch (error) {

        documentName =
            encodedName;
    }


    if (!documentName) {

        showMessage(
            "Document name is missing.",
            "error"
        );

        return;
    }


    if (resultContent) {

        resultContent.innerHTML = `
            <section class="result-card">

                <h3>
                    Loading document...
                </h3>

            </section>
        `;
    }


    if (resultPanel) {

        resultPanel.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/documents/${encodeURIComponent(
                    documentName
                )}`
            );


        if (!response.ok) {

            throw new Error(
                `Unable to load document (${response.status}).`
            );
        }


        let result =
            await response.json();


        if (
            result &&
            result.result &&
            typeof result.result === "object"
        ) {

            result =
                result.result;
        }


        displayProcessingResult(
            result
        );


    } catch (error) {

        console.error(
            "Failed to load document:",
            error
        );


        showMessage(
            error.message ||
            "Unable to load document.",
            "error"
        );


        if (resultContent) {

            resultContent.innerHTML = `
                <section class="result-card">

                    <h3>
                        Error
                    </h3>

                    <p class="missing-value">
                        ${escapeHtml(
                            error.message ||
                            "Unable to load document."
                        )}
                    </p>

                </section>
            `;
        }
    }
}


/*
 * Make the function available to inline HTML onclick handlers.
 */

window.viewDocument =
    viewDocument;


// ============================================================
// DISPLAY PROCESSING RESULT
// ============================================================

function displayProcessingResult(result) {

    if (!resultContent) {
        return;
    }


    if (!result) {

        resultContent.innerHTML = `
            <section class="result-card">

                <h3>
                    No Result
                </h3>

                <p class="missing-value">
                    No processing result was returned.
                </p>

            </section>
        `;

        return;
    }


    /*
     * Sometimes the complete API response is wrapped
     * inside a "data" property.
     */

    if (
        result.data &&
        typeof result.data === "object" &&
        !Array.isArray(result.data) &&
        (
            result.result === undefined ||
            result.document_name === undefined
        )
    ) {

        result =
            {
                ...result.data,
                ...result
            };
    }


    const documentName =
        result.document_name ||
        result.filename ||
        result.file_name ||
        result.name ||
        "Processed Document";


    const type =
        result.document_type ||
        result.type ||
        "Unknown";


    const status =
        result.status ||
        result.processing_status ||
        "Unknown";


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
                            formatDocumentType(type)
                        )}
                    </strong>
                </p>

            </div>

            <span
                class="status ${statusClass(status)}"
            >
                ${escapeHtml(status)}
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

            <pre>${escapeHtml(
                JSON.stringify(
                    result,
                    null,
                    2
                )
            )}</pre>

        </details>

    `;


    if (resultPanel) {

        resultPanel.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
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

                <p class="missing-value">
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


    /*
     * IMPORTANT:
     *
     * When AI extraction fails, backend returns something
     * similar to:
     *
     * {
     *     "success": false,
     *     "error_code": "GEMINI_EXTRACTION_FAILED",
     *     "message": "AI extraction failed..."
     * }
     *
     * Do not display this as if it were successful
     * extracted financial data.
     */

    if (
        data.success === false
    ) {

        return `
            <section class="result-card">

                <h3>
                    Extracted Data
                </h3>

                <div class="status status-error">
                    AI Extraction Failed
                </div>

                ${
                    data.error_code
                        ? `
                            <p>
                                <strong>
                                    Error Code:
                                </strong>

                                ${escapeHtml(
                                    data.error_code
                                )}
                            </p>
                          `
                        : ""
                }

                <p class="missing-value">
                    ${escapeHtml(
                        data.message ||
                        "AI extraction failed. Please try the document again."
                    )}
                </p>

            </section>
        `;
    }


    /*
     * Unwrap nested data object if required.
     */

    if (
        data.data &&
        typeof data.data === "object" &&
        !Array.isArray(data.data)
    ) {

        data =
            data.data;
    }


    let html = `

        <section class="result-card">

            <h3>
                Extracted Data
            </h3>

    `;


    // ========================================================
    // DOCUMENT TYPE
    // ========================================================

    if (data.document_type) {

        html += `

            <div class="key-value-grid">

                ${renderInfoCard(
                    "Document Type",
                    formatDocumentType(
                        data.document_type
                    )
                )}

            </div>

        `;
    }


    // ========================================================
    // FIELDS
    // ========================================================

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
                rawValue
            ]
            of Object.entries(
                data.fields
            )
        ) {

            const value =
                getDisplayValue(
                    rawValue
                );


            /*
             * reporting_periods gets its own section.
             */

            if (
                key === "reporting_periods"
            ) {
                continue;
            }


            html += `

                <div class="key-value-item">

                    <div class="key">

                        ${escapeHtml(
                            formatFieldName(key)
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


    // ========================================================
    // DIRECT FIELDS
    // ========================================================

    const reservedKeys =
        new Set([
            "fields",
            "statement_items",
            "line_items",
            "reporting_periods",
            "evidence",
            "document_type",
            "success",
            "message",
            "error",
            "error_code"
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
            reservedKeys.has(key)
        ) {
            continue;
        }


        if (
            value === null ||
            typeof value !== "object"
        ) {

            directFields[key] =
                value;
        }
    }


    if (
        Object.keys(
            directFields
        ).length > 0
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
                            formatFieldName(key)
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


    // ========================================================
    // REPORTING PERIODS
    // ========================================================

    let reportingPeriods =
        data.reporting_periods;


    /*
     * Some extraction responses place reporting_periods
     * inside fields.
     */

    if (
        reportingPeriods === undefined &&
        data.fields
    ) {

        reportingPeriods =
            data.fields.reporting_periods;
    }


    if (
        reportingPeriods !== null &&
        reportingPeriods !== undefined
    ) {

        if (
            reportingPeriods &&
            typeof reportingPeriods === "object" &&
            !Array.isArray(reportingPeriods) &&
            Object.prototype.hasOwnProperty.call(
                reportingPeriods,
                "value"
            )
        ) {

            reportingPeriods =
                reportingPeriods.value;
        }


        if (
            Array.isArray(
                reportingPeriods
            )
        ) {

            reportingPeriods =
                reportingPeriods
                    .map(period => {

                        if (
                            period &&
                            typeof period === "object"
                        ) {

                            return (
                                period.period ||
                                period.value ||
                                ""
                            );
                        }

                        return period;

                    })
                    .filter(Boolean)
                    .join(" | ");
        }


        html += `

            <h4>
                Reporting Periods
            </h4>

            <div class="key-value-grid">

                ${renderInfoCard(
                    "Reporting Periods",
                    reportingPeriods
                )}

            </div>

        `;
    }


    // ========================================================
    // FINANCIAL STATEMENT ITEMS
    // ========================================================

    if (
        Array.isArray(
            data.statement_items
        ) &&
        data.statement_items.length > 0
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

            const itemName =
                item.line_item ||
                item.item ||
                item.label ||
                "—";


            const schedule =
                item.schedule ||
                "—";


            const values =
                Array.isArray(
                    item.values
                )
                    ? item.values
                    : [];


            let valuesHtml =
                "—";


            if (
                values.length > 0
            ) {

                valuesHtml =
                    values
                        .map(value => {

                            const period =
                                value?.period ||
                                "";


                            const actualValue =
                                getDisplayValue(
                                    value?.value
                                );


                            return `

                                <div>

                                    ${
                                        period
                                            ? `
                                                <strong>
                                                    ${escapeHtml(
                                                        period
                                                    )}
                                                </strong>
                                                :
                                              `
                                            : ""
                                    }

                                    ${formatValue(
                                        actualValue
                                    )}

                                </div>

                            `;

                        })
                        .join("");
            }


            html += `

                <tr>

                    <td>
                        ${escapeHtml(
                            itemName
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            schedule
                        )}
                    </td>

                    <td>
                        ${valuesHtml}
                    </td>

                    <td>
                        ${formatEvidence(
                            item.evidence
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


    // ========================================================
    // INVOICE LINE ITEMS
    // ========================================================

    if (
        Array.isArray(
            data.line_items
        ) &&
        data.line_items.length > 0
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

            const description =
                item.description ??
                "—";


            const quantity =
                item.quantity ??
                item.qty ??
                "—";


            const unitPrice =
                item.unit_price ??
                item.unitPrice ??
                item.price ??
                "—";


            const amount =
                item.amount ??
                item.line_total ??
                item.line_total_amount ??
                "—";


            html += `

                <tr>

                    <td>
                        ${formatValue(
                            description
                        )}
                    </td>

                    <td>
                        ${formatValue(
                            quantity
                        )}
                    </td>

                    <td>
                        ${formatValue(
                            unitPrice
                        )}
                    </td>

                    <td>
                        ${formatValue(
                            amount
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


    // ========================================================
    // DOCUMENT-LEVEL EVIDENCE
    // ========================================================

    if (
        data.evidence
    ) {

        const evidenceText =
            typeof data.evidence === "string"
                ? data.evidence
                : (
                    data.evidence.source_text ||
                    data.evidence.text ||
                    data.evidence.raw_text ||
                    ""
                );


        if (evidenceText) {

            html += `

                <h4>
                    Document Evidence
                </h4>

                <details>

                    <summary>
                        View extracted evidence
                    </summary>

                    <div class="evidence-text">

                        ${escapeHtml(
                            evidenceText
                        )}

                    </div>

                </details>

            `;
        }
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

                <p class="missing-value">
                    No financial validation result available.
                </p>

            </section>
        `;
    }


    const overallStatus =
        validation.overall_status ||
        validation.status ||
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


    if (
        validation.message
    ) {

        html += `

            <p>
                ${escapeHtml(
                    validation.message
                )}
            </p>

        `;
    }


    if (
        !checks.length
    ) {

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

            const checkName =
                check.name ||
                check.check ||
                check.rule ||
                "—";


            const formula =
                check.formula ||
                "—";


            const period =
                check.period ||
                "—";


            const calculated =
                check.calculated_value ??
                check.calculated ??
                null;


            const reported =
                check.reported_value ??
                check.reported ??
                null;


            const variance =
                check.variance ??
                null;


            const checkStatus =
                check.status ||
                "NOT_APPLICABLE";


            html += `

                <tr>

                    <td>
                        ${escapeHtml(
                            checkName
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            formula
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            period
                        )}
                    </td>

                    <td>
                        ${formatValue(
                            calculated
                        )}
                    </td>

                    <td>
                        ${formatValue(
                            reported
                        )}
                    </td>

                    <td>
                        ${formatValue(
                            variance
                        )}
                    </td>

                    <td>

                        <span
                            class="status ${statusClass(
                                checkStatus
                            )}"
                        >
                            ${escapeHtml(
                                checkStatus
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


    /*
     * Display validation tolerance if backend supplies it.
     */

    if (
        validation.tolerance !== undefined ||
        validation.relative_tolerance !== undefined
    ) {

        html += `

            <div class="key-value-grid">

                ${
                    validation.tolerance !== undefined
                        ? renderInfoCard(
                            "Tolerance",
                            validation.tolerance
                        )
                        : ""
                }

                ${
                    validation.relative_tolerance !== undefined
                        ? renderInfoCard(
                            "Relative Tolerance",
                            validation.relative_tolerance
                        )
                        : ""
                }

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


    /*
     * Remove duplicate issue messages.
     */

    const uniqueIssues = [];


    const seen =
        new Set();


    for (
        const issue
        of issues
    ) {

        const message =
            typeof issue === "string"
                ? issue
                : (
                    issue?.message ||
                    issue?.description ||
                    JSON.stringify(issue)
                );


        const normalized =
            String(message)
                .trim();


        if (
            normalized &&
            !seen.has(normalized)
        ) {

            seen.add(
                normalized
            );

            uniqueIssues.push(
                normalized
            );
        }
    }


    if (
        !uniqueIssues.length
    ) {

        return "";
    }


    return `

        <section class="result-card issues">

            <h3>
                Issues
            </h3>

            <ul>

                ${uniqueIssues
                    .map(issue => `

                        <li>
                            ${escapeHtml(
                                issue
                            )}
                        </li>

                    `)
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
        async function () {

            await loadDocuments();

        }
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