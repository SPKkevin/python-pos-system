<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import api ,{safeRequest} from '@/services/api'


///Localhost:5173/orders
const router = useRouter()
const route = useRoute()
const orderId = Number(route.params.id)

const order = ref<any>(null)
const items = ref<any[]>([])
const newItem = ref({
  name: '',
  price: 0,
  qty: 1
})
///初始渲染設定
async function loadOrder() {
    const res = await safeRequest(() =>
    api.get(`/orders/${orderId}`)
    )
    if (!res) return
    order.value = res.data.order
    items.value = res.data.items
}
///結帳功能
async function payBild() {
  if (!confirm('確定要結帳嗎？')) return
  const res = await safeRequest(() =>
  api.patch(`/orders/${route.params.id}/pay`,
    {
      payment_method: "cash",
      paid_amount: order.value.total
    }
  )
  )
  if (!res) return
  const order_id = res.data.order_id
  await loadOrder() // 重新抓資料
  alert(`${order_id}訂單結帳成功`)
  router.push('/orders')
}

///加單防錯判斷
function validateNewItem(): boolean {
  const it = newItem.value;
  const nameOk = it.name.trim() !== '';
  const priceOk = it.price > 0;
  const qtyOk = it.qty > 0;

  if (!nameOk || !priceOk || !qtyOk) {
    alert('商品資料不完整');
    return false;
  }
  return true;
}
///加單功能
async function addItem() {
  if (!validateNewItem())return
  const res  = await safeRequest(() =>
  api.post(`/orders/${order.value.id}/items`,
    {
      items: [newItem.value]
    })
  )
  if (!res)return
  // 重新抓一次訂單資料
  await loadOrder()
  newItem.value = { name: '', price: 0, qty: 1 }
}

///刪除功能
async function deleteItem(itemId: number) {
  const res = await safeRequest(() =>
  api.delete(`/orders/${order.value.id}/items/${itemId}`)
  )
  if (!res)return 
  await loadOrder()
}


onMounted(loadOrder)
</script>

<template>
  <div style="padding: 40px">
    <h1>訂單明細 #{{ orderId }}</h1>

    <div v-if="order" style="margin-bottom: 12px">
      <div>狀態：{{ order.status }}</div>
      <div>總額：{{ order.total }}</div>
      <div>建立時間：{{ order.created_at }}</div>
      <div>付款方式：{{ order.payment_method }}</div>

      <button
        v-if="order.status === 'OPEN'"
        @click="payBild"
        style="margin-top: 8px"
      >
        結帳
      </button>
    </div>

    <table class="orders">
      <thead>
        <tr>
          <th>品名</th>
          <th>價格(不能是0)</th>
          <th>數量</th>
          <th>操作</th>
        </tr>
      </thead>

      <tbody>
        <!-- 新增品項列（只在 OPEN 顯示） -->
        <tr v-if="order && order.status === 'OPEN'">
          <td><input v-model="newItem.name" /></td>
          <td><input v-model.number="newItem.price" type="number" /></td>
          <td><input v-model.number="newItem.qty" type="number" /></td>
          <td style="white-space: nowrap">
            <button @click="addItem">新增品項</button>
          </td>
        </tr>

        <!-- 現有品項 -->
        <tr v-for="it in items" :key="it.id">
          <td>{{ it.name }}</td>
          <td>{{ it.price }}</td>
          <td>{{ it.qty }}</td>
          <td v-if="order && order.status === 'OPEN'">
            <button @click="deleteItem(it.id)">刪除</button>
          </td>
          <td v-else></td>
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
