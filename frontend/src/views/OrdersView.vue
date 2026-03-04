<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api, {safeRequest} from '@/services/api'
///cd vue_project
/// npm run dev
///Localhost:5173/order


// 這個陣列用來裝 API 回傳的訂單列表
const orders = ref<any[]>([])

async function loadOrders() {
  const res = await safeRequest(() =>
  api.get('/orders/recent')

  )
  if (!res)return
  orders.value = res.data
}

// 這裡就是「頁面載入後自動跑一次」的地方
onMounted(loadOrders)

</script>

<template>
  <div style="padding: 40px">
    <h1>最近訂單</h1>

    <table class="orders" >
      <thead>
        <tr>
          <th>ID</th>
          <th>總額</th>
          <th>狀態</th>
          <th>建立時間</th>
          <button class="btn" @click="loadOrders">重新整理</button>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in orders" :key="o.id">
          <td>
            <router-link :to="`/orders/${o.id}`">{{ o.id }}</router-link>
          </td>
          <td>{{ o.total }}</td>
          <td>{{ o.status }}</td>
          <td>{{ o.created_at }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.orders {
  margin: 0 auto;              /* 置中 */
  border-collapse: collapse;    /* 邊框合併，變乾淨 */
  min-width: 520px;
  background: #fff;
  font-size: 14px;
}

.orders th,
.orders td {
  border: 1px solid #d9d9d9;    /* 細邊框 */
  padding: 10px 14px;           /* 內距一致 */
  text-align: center;           /* 對齊 */
  vertical-align: middle;
  white-space: nowrap;
}

.orders th {
  background: #f5f5f5;          /* 表頭淡底 */
  font-weight: 600;
}

.orders tr:nth-child(even) td {
  background: #fafafa;          /* 斑馬紋 */
}

.orders tr:hover td {
  background: #f0f7ff;          /* 滑過高亮 */
}

.btn {
  margin-left: 12px;
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  background: #fff;
  cursor: pointer;
}
</style>
