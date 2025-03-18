<template>
  <div class="beancount-editor">
    <h1>Beancount Entries Editor</h1>

    <!-- Filter section -->
    <div class="filter-section">
      <el-row :gutter="10">
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-input
            v-model="filters.narration"
            placeholder="Filter by Narration"
            clearable
            @clear="loadTransactions"
            @keyup.enter="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-input
            v-model="filters.account"
            placeholder="Filter by Account"
            clearable
            @clear="loadTransactions"
            @keyup.enter="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-select
            v-model="filters.tag"
            placeholder="Filter by Tag"
            clearable
            style="width: 100%"
            @clear="loadTransactions"
            @change="loadTransactions"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-col>
      </el-row>
      <el-row :gutter="10" style="margin-top: 10px;">
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-date-picker
            v-model="filters.fromDate"
            type="date"
            placeholder="From Date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
            @clear="loadTransactions"
            @change="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-date-picker
            v-model="filters.toDate"
            type="date"
            placeholder="To Date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
            @clear="loadTransactions"
            @change="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-select
            v-model="filters.currency"
            placeholder="Filter by Currency"
            clearable
            style="width: 100%;"
            @clear="loadTransactions"
            @change="loadTransactions"
          >
            <el-option
              v-for="currency in availableCurrencies"
              :key="currency"
              :label="currency"
              :value="currency"
            />
          </el-select>
        </el-col>
      </el-row>
      <el-row :gutter="10" style="margin-top: 10px;">
        <el-col :span="24">
          <el-button type="primary" @click="loadTransactions">
            <el-icon><Search /></el-icon> Search
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon> Reset Filters
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- Loading indicator -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- Table section -->
    <div v-else>
      <el-table :data="transactions" style="width: 100%" border v-loading="loading">
        <el-table-column label="Flag" width="80" align="center">
          <template #default="scope">
            <el-select v-model="scope.row.flag" style="width: 60px">
              <el-option label="*" value="*" />
              <el-option label="!" value="!" />
            </el-select>
          </template>
        </el-table-column>

        <el-table-column label="Date" width="150" align="center">
          <template #default="scope">
            <el-date-picker
              v-model="scope.row.date"
              type="date"
              placeholder="Select date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </template>
        </el-table-column>

        <el-table-column label="Payee" min-width="150">
          <template #default="scope">
            <el-input v-model="scope.row.payee" placeholder="Enter payee" />
          </template>
        </el-table-column>

        <el-table-column label="Narration" min-width="200">
          <template #default="scope">
            <el-input v-model="scope.row.narration" placeholder="Enter narration" />
          </template>
        </el-table-column>

        <el-table-column label="Tags" min-width="150">
          <template #default="scope">
            <div class="tag-container">
              <el-tag
                v-for="tag in scope.row.tags"
                :key="tag"
                closable
                class="tag-item"
                @close="removeTag(scope.row, tag)"
              >
                {{ tag }}
              </el-tag>
              <el-button
                size="small"
                type="primary"
                plain
                @click="showTagInput(scope.row)"
              >
                + Tag
              </el-button>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="180" align="center">
          <template #default="scope">
            <el-button
              size="small"
              type="primary"
              @click="editPostings(scope.row)"
            >
              Edit Postings
            </el-button>
            <el-button
              size="small"
              type="success"
              circle
              @click="saveTransaction(scope.row)"
              :loading="scope.row.saving"
            >
              <el-icon><Check /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalItems"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <!-- Save all changes button -->
      <div class="action-buttons">
        <el-button type="success" @click="saveAllChanges" :loading="savingAll">
          <el-icon><Upload /></el-icon> Save All Changes
        </el-button>
      </div>
    </div>

    <!-- Tag Input Dialog -->
    <el-dialog
      v-model="tagDialogVisible"
      title="Add Tag"
      width="30%"
    >
      <el-input
        v-model="newTagValue"
        placeholder="Enter tag name"
        @keyup.enter="confirmAddTag"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="tagDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="confirmAddTag">Confirm</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Postings Dialog -->
    <el-dialog
      v-model="postingsDialogVisible"
      title="Edit Postings"
      width="80%"
    >
      <div v-if="currentTransaction">
        <div v-for="(posting, index) in currentTransaction.postings" :key="index" class="posting-editor">
          <el-divider v-if="index > 0" />
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="Account">
                <el-autocomplete
                  v-model="posting.account"
                  :fetch-suggestions="queryAccounts"
                  placeholder="Enter account"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="Amount">
                <el-input v-model="posting.units.number" placeholder="Amount" />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="Currency">
                <el-select v-model="posting.units.currency" placeholder="Currency" style="width: 100%">
                  <el-option
                    v-for="currency in availableCurrencies"
                    :key="currency"
                    :label="currency"
                    :value="currency"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="Missing">
                <el-switch v-model="posting.units.is_missing" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row>
            <el-col :span="24" class="posting-actions">
              <el-button
                v-if="currentTransaction.postings.length > 2"
                type="danger"
                size="small"
                @click="removePosting(index)"
              >
                Remove Posting
              </el-button>
            </el-col>
          </el-row>
        </div>

        <div class="posting-actions">
          <el-button type="primary" @click="addPosting">
            Add Posting
          </el-button>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="postingsDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="savePostings">Save Postings</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import { Delete, Plus, Upload, Check, Search, Refresh } from '@element-plus/icons-vue';
import axios from 'axios';

// API base URL - change this to match your FastAPI server
const API_BASE_URL = 'http://localhost:8000/api';

export default {
  name: 'BeancountEditor',
  components: {
    Delete,
    Plus,
    Upload,
    Check,
    Search,
    Refresh
  },
  setup() {
    // State
    const transactions = ref([]);
    const availableAccounts = ref([]);
    const availableTags = ref([]);
    const availableCurrencies = ref([]);
    const loading = ref(false);
    const savingAll = ref(false);
    const tagDialogVisible = ref(false);
    const postingsDialogVisible = ref(false);
    const newTagValue = ref('');
    const currentTransaction = ref(null);
    const currentTaggedTransaction = ref(null);
    const totalItems = ref(0);
    const currentPage = ref(1);
    const pageSize = ref(20);

    // Filters
    const filters = reactive({
      narration: '',
      account: '',
      fromDate: '',
      toDate: '',
      tag: '',
      currency: ''
    });

    // Load reference data
    const loadReferenceData = async () => {
      try {
        const [accountsResponse, tagsResponse, currenciesResponse] = await Promise.all([
          axios.get(`${API_BASE_URL}/accounts`),
          axios.get(`${API_BASE_URL}/tags`),
          axios.get(`${API_BASE_URL}/currencies`)
        ]);

        availableAccounts.value = accountsResponse.data;
        availableTags.value = tagsResponse.data;
        availableCurrencies.value = currenciesResponse.data;
      } catch (error) {
        console.error('Error loading reference data:', error);
        ElMessage.error('Failed to load reference data');
      }
    };

    // Load transactions with current filters and pagination
    const loadTransactions = async () => {
      loading.value = true;
      try {
        // Build query parameters
        const params = {
          page: currentPage.value,
          page_size: pageSize.value
        };

        if (filters.narration) params.narration = filters.narration;
        if (filters.account) params.account = filters.account;
        if (filters.fromDate) params.from_date = filters.fromDate;
        if (filters.toDate) params.to_date = filters.toDate;
        if (filters.tag) params.tag = filters.tag;
        if (filters.currency) params.currency = filters.currency;

        const response = await axios.get(`${API_BASE_URL}/transactions`, { params });

        // Update state
        transactions.value = response.data.data.items;
        totalItems.value = response.data.data.total;

        // Add saving flag to each transaction
        transactions.value.forEach(tx => {
          tx.saving = false;
        });
      } catch (error) {
        console.error('Error loading transactions:', error);
        ElMessage.error('Failed to load transactions');
      } finally {
        loading.value = false;
      }
    };

    // Reset all filters
    const resetFilters = () => {
      Object.keys(filters).forEach(key => {
        filters[key] = '';
      });
      loadTransactions();
    };

    // Pagination event handlers
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize;
      loadTransactions();
    };

    const handleCurrentChange = (newPage) => {
      currentPage.value = newPage;
      loadTransactions();
    };

    // Tag operations
    const showTagInput = (transaction) => {
      currentTaggedTransaction.value = transaction;
      newTagValue.value = '';
      tagDialogVisible.value = true;
    };

    const confirmAddTag = () => {
      const tag = newTagValue.value.trim();
      if (tag && currentTaggedTransaction.value) {
        // Create a new array to trigger reactivity
        currentTaggedTransaction.value.tags = [
          ...currentTaggedTransaction.value.tags,
          tag
        ];
      }
      tagDialogVisible.value = false;
    };

    const removeTag = (transaction, tag) => {
      transaction.tags = transaction.tags.filter(t => t !== tag);
    };

    // Posting operations
    const editPostings = (transaction) => {
      currentTransaction.value = JSON.parse(JSON.stringify(transaction)); // Deep clone
      postingsDialogVisible.value = true;
    };

    const addPosting = () => {
      if (!currentTransaction.value) return;

      // Create a default empty posting
      const newPosting = {
        account: '',
        units: {
          number: null,
          currency: availableCurrencies.value[0] || 'USD',
          is_missing: false
        },
        cost: null,
        price: null,
        flag: null,
        meta: {}
      };

      currentTransaction.value.postings.push(newPosting);
    };

    const removePosting = (index) => {
      if (!currentTransaction.value || currentTransaction.value.postings.length <= 2) return;
      currentTransaction.value.postings.splice(index, 1);
    };

    const savePostings = () => {
      if (!currentTransaction.value) return;

      // Find the original transaction and update it
      const index = transactions.value.findIndex(t =>
        t.meta.beanbot_uuid === currentTransaction.value.meta.beanbot_uuid
      );

      if (index >= 0) {
        // Only update the postings
        transactions.value[index].postings = currentTransaction.value.postings;
      }

      postingsDialogVisible.value = false;
    };

    // Account autocomplete
    const queryAccounts = (queryString, callback) => {
      const results = queryString
        ? availableAccounts.value.filter(account =>
            account.toLowerCase().includes(queryString.toLowerCase())
          )
        : availableAccounts.value;

      callback(results.map(account => ({ value: account })));
    };

    // Save a single transaction
    const saveTransaction = async (transaction) => {
      transaction.saving = true;

      try {
        const uuid = transaction.meta.beanbot_uuid;
        await axios.put(`${API_BASE_URL}/transactions/${uuid}`, transaction);

        ElMessage.success('Transaction updated successfully');
      } catch (error) {
        console.error('Error saving transaction:', error);
        ElMessage.error('Failed to save transaction');
      } finally {
        transaction.saving = false;
      }
    };

    // Save all changes to file
    const saveAllChanges = async () => {
      savingAll.value = true;

      try {
        await axios.post(`${API_BASE_URL}/save`);

        ElMessage.success('All changes saved to file');
      } catch (error) {
        console.error('Error saving changes:', error);
        ElMessage.error('Failed to save changes to file');
      } finally {
        savingAll.value = false;
      }
    };

    // Initialize
    onMounted(async () => {
      await loadReferenceData();
      await loadTransactions();
    });

    return {
      // State
      transactions,
      availableAccounts,
      availableTags,
      availableCurrencies,
      loading,
      savingAll,
      filters,
      tagDialogVisible,
      postingsDialogVisible,
      newTagValue,
      currentTransaction,
      currentTaggedTransaction,
      totalItems,
      currentPage,
      pageSize,

      // Methods
      loadTransactions,
      resetFilters,
      handleSizeChange,
      handleCurrentChange,
      showTagInput,
      confirmAddTag,
      removeTag,
      editPostings,
      addPosting,
      removePosting,
      savePostings,
      queryAccounts,
      saveTransaction,
      saveAllChanges
    };
  }
};
</script>

<style scoped>
.beancount-editor {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.tag-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.posting-editor {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.posting-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.loading-container {
  padding: 20px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
    gap: 10px;
  }

  .action-buttons .el-button {
    width: 100%;
  }
}
</style>
