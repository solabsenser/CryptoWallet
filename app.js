const API = "";

let tg = window.Telegram.WebApp;

let currentUser = null;

let telegramId = null;

let username = null;

let firstName = null;

// ======================================
// INIT
// ======================================

window.addEventListener("load", async () => {

    tg.expand();

    tg.ready();

    initTelegram();

    initNavigation();

    initFab();

    await login();

    hideLoader();

});

// ======================================
// TELEGRAM
// ======================================

function initTelegram() {

    const user = tg.initDataUnsafe.user;

    if (!user) {

        console.error("Telegram user not found");

        return;

    }

    telegramId = user.id;

    username = user.username || "";

    firstName = user.first_name || "";

}

// ======================================
// LOGIN
// ======================================

async function login() {

    const response = await fetch(
        "/api/login",
        {
            method: "POST",
            headers: {
                "Content-Type":
                "application/json"
            },
            body: JSON.stringify({
                telegram_id: telegramId,
                username: username,
                first_name: firstName
            })
        }
    );

    const data = await response.json();

    currentUser = data.user;

    renderProfile();

    renderDashboard();

    checkWallet();

}

// ======================================
// PROFILE
// ======================================

function renderProfile() {

    document.getElementById(
        "username"
    ).innerText =
        currentUser.username ||
        firstName;

    document.getElementById(
        "telegram-id"
    ).innerText =
        currentUser.telegram_id;

}

// ======================================
// DASHBOARD
// ======================================

function renderDashboard() {

    document.getElementById(
        "portfolio-value"
    ).innerText =
        Number(
            currentUser.balance || 0
        ).toFixed(2) + " TON";

    document.getElementById(
        "ton-balance"
    ).innerText =
        Number(
            currentUser.balance || 0
        ).toFixed(2);

    document.getElementById(
        "assets-ton"
    ).innerText =
        Number(
            currentUser.balance || 0
        ).toFixed(2);

    if (currentUser.wallet_address) {

        document.getElementById(
            "wallet-address"
        ).innerText =
            currentUser.wallet_address;

        document.getElementById(
            "receive-wallet"
        ).innerText =
            currentUser.wallet_address;

    }

}

// ======================================
// WALLET CHECK
// ======================================

function checkWallet() {

    if (
        !currentUser.wallet_created
    ) {

        document
        .getElementById(
            "create-wallet-btn"
        )
        .style.display =
        "block";

    }

}

// ======================================
// LOADER
// ======================================

function hideLoader() {

    setTimeout(() => {

        document
        .getElementById(
            "loader"
        )
        .style.display =
        "none";

    }, 1000);

}

// ======================================
// NAVIGATION
// ======================================

function initNavigation() {

    const buttons =
    document.querySelectorAll(
        ".bottom-nav button"
    );

    buttons.forEach(btn => {

        btn.addEventListener(
            "click",
            () => {

                const page =
                btn.dataset.page;

                document
                .querySelectorAll(
                    ".page"
                )
                .forEach(p => {

                    p.classList.remove(
                        "active"
                    );

                });

                document
                .getElementById(
                    page
                )
                .classList.add(
                    "active"
                );

            }
        );

    });

}

// ======================================
// FLOAT BUTTON
// ======================================

function initFab() {

    const fab =
    document.getElementById(
        "fab"
    );

    const menu =
    document.getElementById(
        "action-menu"
    );

    fab.addEventListener(
        "click",
        () => {

            if (
                menu.style.display
                === "flex"
            ) {

                menu.style.display =
                "none";

            } else {

                menu.style.display =
                "flex";

            }

        }
    );

}

// ======================================
// CREATE WALLET
// ======================================

document
.getElementById("create-wallet-btn")
.addEventListener(
    "click",
    createWallet
);

async function createWallet() {

    const response = await fetch(
        "/api/create-wallet",
        {
            method: "POST",
            headers: {
                "Content-Type":
                "application/json"
            },
            body: JSON.stringify({
                telegram_id: telegramId
            })
        }
    );

    const data =
    await response.json();

    if (!data.success) {

        showToast(
            data.message ||
            "Wallet exists"
        );

        return;
    }

    document
    .getElementById(
        "seed-phrase"
    )
    .value =
    data.seed_phrase;

    document
    .getElementById(
        "wallet-modal"
    )
    .classList.add(
        "active"
    );

}

// ======================================
// CONFIRM WALLET
// ======================================

document
.getElementById(
    "confirm-wallet"
)
.addEventListener(
    "click",
    async () => {

        document
        .getElementById(
            "wallet-modal"
        )
        .classList.remove(
            "active"
        );

        await refreshProfile();

        showToast(
            "Wallet Created"
        );

    }
);

// ======================================
// IMPORT WALLET
// ======================================

document
.getElementById(
    "import-wallet-btn"
)
.addEventListener(
    "click",
    () => {

        document
        .getElementById(
            "import-modal"
        )
        .classList.add(
            "active"
        );

    }
);

document
.getElementById(
    "import-submit"
)
.addEventListener(
    "click",
    importWallet
);

async function importWallet() {

    const seed =
    document
    .getElementById(
        "import-seed"
    )
    .value.trim();

    if (!seed) {

        showToast(
            "Enter seed phrase"
        );

        return;
    }

    const response =
    await fetch(
        "/api/import-wallet",
        {
            method: "POST",
            headers: {
                "Content-Type":
                "application/json"
            },
            body: JSON.stringify({
                telegram_id:
                telegramId,
                seed_phrase:
                seed
            })
        }
    );

    const data =
    await response.json();

    if (data.success) {

        document
        .getElementById(
            "import-modal"
        )
        .classList.remove(
            "active"
        );

        await refreshProfile();

        showToast(
            "Wallet Imported"
        );

    }

}

// ======================================
// REFRESH PROFILE
// ======================================

async function refreshProfile() {

    const response =
    await fetch(
        `/api/profile/${telegramId}`
    );

    const data =
    await response.json();

    currentUser =
    data.user;

    renderProfile();

    renderDashboard();

}

// ======================================
// HISTORY
// ======================================

async function loadHistory() {

    const response =
    await fetch(
        `/api/history/${telegramId}`
    );

    const data =
    await response.json();

    const container =
    document.getElementById(
        "transactions"
    );

    container.innerHTML = "";

    if (
        !data.transactions ||
        data.transactions.length === 0
    ) {

        container.innerHTML =
        `
        <p class="empty">
        No transactions
        </p>
        `;

        return;
    }

    data.transactions.forEach(
        tx => {

            container.innerHTML +=
            `
            <div class="tx-card">

                <div class="tx-top">

                    <span>
                        ${tx.tx_type}
                    </span>

                    <span class="tx-amount">

                        ${tx.amount}

                    </span>

                </div>

                <div class="tx-date">

                    ${tx.created_at}

                </div>

            </div>
            `;

        }
    );

}

// ======================================
// SEND MODAL
// ======================================

document
.getElementById("open-send")
.addEventListener(
    "click",
    () => {

        document
        .getElementById(
            "send-modal"
        )
        .classList.add(
            "active"
        );

    }
);

// ======================================
// RECEIVE MODAL
// ======================================

document
.getElementById("open-receive")
.addEventListener(
    "click",
    () => {

        document
        .getElementById(
            "receive-modal"
        )
        .classList.add(
            "active"
        );

    }
);

// ======================================
// SEND
// ======================================

document
.getElementById("send-btn")
.addEventListener(
    "click",
    sendCoins
);

async function sendCoins() {

    const wallet =
    document
    .getElementById(
        "receiver-wallet"
    )
    .value.trim();

    const amount =
    parseFloat(
        document
        .getElementById(
            "send-amount"
        )
        .value
    );

    if (!wallet) {

        showToast(
            "Enter wallet"
        );

        return;
    }

    if (!amount || amount <= 0) {

        showToast(
            "Invalid amount"
        );

        return;
    }

    const response =
    await fetch(
        "/api/send",
        {
            method:"POST",

            headers:{
                "Content-Type":
                "application/json"
            },

            body:JSON.stringify({

                sender_id:
                telegramId,

                receiver_wallet:
                wallet,

                amount:
                amount

            })
        }
    );

    const data =
    await response.json();

    if (data.success) {

        document
        .getElementById(
            "send-modal"
        )
        .classList.remove(
            "active"
        );

        showToast(
            "Transfer completed"
        );

        await refreshProfile();

        await loadHistory();

    }
    else {

        showToast(
            data.detail ||
            "Transfer failed"
        );

    }

}

// ======================================
// COPY ADDRESS
// ======================================

document
.getElementById(
    "copy-wallet"
)
.addEventListener(
    "click",
    async () => {

        const wallet =
        document
        .getElementById(
            "receive-wallet"
        )
        .innerText;

        await navigator
        .clipboard
        .writeText(wallet);

        showToast(
            "Address copied"
        );

    }
);

// ======================================
// REFERRAL
// ======================================

document
.getElementById(
    "generate-ref"
)
.addEventListener(
    "click",
    generateReferral
);

async function generateReferral() {

    const response =
    await fetch(
        "/api/referral/create",
        {
            method:"POST",

            headers:{
                "Content-Type":
                "application/json"
            },

            body:JSON.stringify({

                telegram_id:
                telegramId

            })
        }
    );

    const data =
    await response.json();

    if (data.success) {

        document
        .getElementById(
            "ref-code"
        )
        .innerText =
        data.code;

        showToast(
            "Referral created"
        );

    }

}

// ======================================
// TOAST
// ======================================

function showToast(text) {

    let container =
    document.getElementById(
        "toast-container"
    );

    if (!container) {

        container =
        document.createElement(
            "div"
        );

        container.id =
        "toast-container";

        document.body.appendChild(
            container
        );

    }

    const toast =
    document.createElement(
        "div"
    );

    toast.className =
    "toast";

    toast.innerText =
    text;

    container.appendChild(
        toast
    );

    setTimeout(() => {

        toast.remove();

    }, 3000);

}

// ======================================
// CLOSE MODALS
// ======================================

document
.querySelectorAll(".modal")
.forEach(modal => {

    modal.addEventListener(
        "click",
        e => {

            if (
                e.target === modal
            ) {

                modal.classList.remove(
                    "active"
                );

            }

        }
    );

});

// ======================================
// INITIAL DATA
// ======================================

setTimeout(
    async () => {

        await loadHistory();

    },
    1500
);
