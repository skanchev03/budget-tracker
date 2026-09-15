document.addEventListener("DOMContentLoaded", function () {

    /*
     * Prevent the script from being initialized more than once.
     *
     * This protects us if the script is accidentally included
     * twice in the page.
     */
    if (window.transactionFormInitialized) {
        return;
    }

    window.transactionFormInitialized = true;


    const typeField = document.getElementById("id_type");
    const categoryField = document.getElementById("id_category");
    const subcategoryField = document.getElementById("id_subcategory");


    if (!typeField || !categoryField || !subcategoryField) {
        return;
    }


    /*
     * ---------------------------------------------------------
     * Filter categories according to transaction type
     * ---------------------------------------------------------
     */

    function filterCategories() {

        const selectedType = typeField.value;
        const currentCategory = categoryField.value;

        let currentCategoryIsValid = false;


        Array.from(categoryField.options).forEach(function (option) {

            /*
             * Keep the empty placeholder visible.
             */
            if (!option.value) {
                option.hidden = false;
                return;
            }


            const categoryType = option.dataset.type;


            if (categoryType === selectedType) {

                option.hidden = false;

                if (option.value === currentCategory) {
                    currentCategoryIsValid = true;
                }

            } else {

                option.hidden = true;

            }
        });


        /*
         * Reset category and subcategory if the selected
         * category does not belong to the selected type.
         */
        if (!currentCategoryIsValid) {

            categoryField.value = "";

            resetSubcategory();
        }
    }


    /*
     * ---------------------------------------------------------
     * Reset subcategory
     * ---------------------------------------------------------
     */

    function resetSubcategory() {

        subcategoryField.innerHTML = "";

        const placeholder = document.createElement("option");

        placeholder.value = "";
        placeholder.textContent = "---------";

        subcategoryField.appendChild(placeholder);

        subcategoryField.value = "";
        subcategoryField.disabled = true;
    }


    /*
     * ---------------------------------------------------------
     * Load subcategories
     * ---------------------------------------------------------
     */

    async function loadSubcategories(categoryId) {

        resetSubcategory();


        if (!categoryId) {
            return;
        }


        try {

            const url =
                `/transactions/subcategories/?category_id=${encodeURIComponent(categoryId)}`;


            const response = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });


            if (!response.ok) {
                throw new Error(
                    "Failed to load subcategories."
                );
            }


            const data = await response.json();


            /*
             * Add returned subcategories to the dropdown.
             */
            data.subcategories.forEach(function (subcategory) {

                const option = document.createElement("option");

                option.value = subcategory.id;
                option.textContent = subcategory.name;

                subcategoryField.appendChild(option);
            });


            subcategoryField.disabled = false;

        } catch (error) {

            console.error(
                "Error loading subcategories:",
                error
            );


            subcategoryField.innerHTML = "";

            const errorOption = document.createElement("option");

            errorOption.value = "";
            errorOption.textContent =
                "Unable to load subcategories.";

            subcategoryField.appendChild(errorOption);

            subcategoryField.disabled = true;
        }
    }


    /*
     * ---------------------------------------------------------
     * Transaction type changed
     * ---------------------------------------------------------
     */

    typeField.addEventListener("change", function () {

        filterCategories();

    });


    /*
     * ---------------------------------------------------------
     * Category changed
     * ---------------------------------------------------------
     */

    categoryField.addEventListener("change", function () {

        loadSubcategories(this.value);

    });


    /*
     * ---------------------------------------------------------
     * Initial state
     * ---------------------------------------------------------
     */

    filterCategories();


    if (categoryField.value) {

        loadSubcategories(categoryField.value);

    } else {

        resetSubcategory();

    }

});