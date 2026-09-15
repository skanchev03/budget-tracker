document.addEventListener("DOMContentLoaded", function () {

    /*
     * ---------------------------------------------------------
     * Expenses by Category
     * ---------------------------------------------------------
     */

    const expenseDataElement = document.getElementById(
        "expense-data"
    );

    const expenseChartCanvas = document.getElementById(
        "expenses-by-category-chart"
    );

    if (expenseDataElement && expenseChartCanvas) {

        const expenseCategories = JSON.parse(
            expenseDataElement.textContent
        );

        const labels = expenseCategories.map(
            category => category.category__name
        );

        const data = expenseCategories.map(
            category => Number(category.total)
        );

        if (data.length > 0) {

            new Chart(expenseChartCanvas, {
                type: "doughnut",

                data: {
                    labels: labels,

                    datasets: [
                        {
                            data: data,
                            borderWidth: 0,
                            hoverOffset: 6
                        }
                    ]
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    cutout: "62%",

                    interaction: {
                        intersect: false
                    },

                    plugins: {
                        legend: {
                            position: "right",
                            labels: {
                                padding: 16,
                                usePointStyle: true
                            }
                        },

                        tooltip: {
                            callbacks: {
                                label: function (context) {

                                    const value = Number(
                                        context.parsed
                                    );

                                    return (
                                        context.label
                                        + ": "
                                        + value.toFixed(2)
                                    );
                                }
                            }
                        }
                    }
                }
            });
        }
    }


    /*
     * ---------------------------------------------------------
     * Monthly Income vs Expenses
     * ---------------------------------------------------------
     */

    const monthlyDataElement = document.getElementById(
        "monthly-income-expenses-data"
    );

    const monthlyChartCanvas = document.getElementById(
        "monthly-income-expenses-chart"
    );

    if (monthlyDataElement && monthlyChartCanvas) {

        const parsedMonthlyData = JSON.parse(
            monthlyDataElement.textContent
        );

        const monthlyData = Array.isArray(parsedMonthlyData)
            ? parsedMonthlyData
            : parsedMonthlyData.months;

        if (Array.isArray(monthlyData)) {

            const labels = monthlyData.map(
                month => month.label
            );

            const incomeData = monthlyData.map(
                month => Number(month.income)
            );

            const expenseData = monthlyData.map(
                month => Number(month.expenses)
            );

            /*
             * Check whether there is actually any financial data.
             *
             * The backend still returns the last 12 months even
             * when every value is zero. In that case we should not
             * render an empty-looking Chart.js graph.
             */

            const hasFinancialData =
                incomeData.some(value => value !== 0) ||
                expenseData.some(value => value !== 0);

            const chartContainer =
                monthlyChartCanvas.closest(
                    ".monthly-chart-container"
                );

            if (!hasFinancialData) {

                if (chartContainer) {

                    chartContainer.classList.add(
                        "chart-empty"
                    );

                    const emptyTitle =
                        chartContainer.dataset.emptyTitle;

                    const emptyMessage =
                        chartContainer.dataset.emptyMessage;

                    chartContainer.innerHTML = `
                        <div class="chart-empty-content">
                            <div class="chart-empty-icon">📊</div>

                            <h3>${emptyTitle}</h3>

                            <p>${emptyMessage}</p>

                            <a
                                href="/transactions/create/"
                                class="btn btn-primary"
                            >
                                + Add Transaction
                            </a>
                        </div>
                    `;
                }

            } else {

                new Chart(monthlyChartCanvas, {
                    type: "line",

                    data: {
                        labels: labels,

                        datasets: [
                            {
                                label: "Income",
                                data: incomeData,
                                tension: 0.3,
                                borderWidth: 2,
                                pointRadius: 3,
                                pointHoverRadius: 5,
                                fill: false
                            },

                            {
                                label: "Expenses",
                                data: expenseData,
                                tension: 0.3,
                                borderWidth: 2,
                                pointRadius: 3,
                                pointHoverRadius: 5,
                                fill: false
                            }
                        ]
                    },

                    options: {
                        responsive: true,
                        maintainAspectRatio: false,

                        interaction: {
                            intersect: false,
                            mode: "index"
                        },

                        scales: {
                            x: {
                                grid: {
                                    display: false
                                }
                            },

                            y: {
                                beginAtZero: true,

                                ticks: {
                                    precision: 2
                                }
                            }
                        },

                        plugins: {
                            legend: {
                                position: "top",

                                labels: {
                                    padding: 16,
                                    usePointStyle: true
                                }
                            },

                            tooltip: {
                                callbacks: {
                                    label: function (context) {

                                        const value = Number(
                                            context.parsed.y
                                        );

                                        return (
                                            context.dataset.label
                                            + ": "
                                            + value.toFixed(2)
                                        );
                                    }
                                }
                            }
                        }
                    }
                });
            }
        }
    }
});